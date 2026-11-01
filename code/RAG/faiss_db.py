"""Cosine FAISS storage. JSON metadata; no pickle or executable deserialization."""
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4
import numpy as np
import faiss


class FaissVectorStore:
    def __init__(self, dimension):
        self.index = faiss.IndexFlatIP(dimension)
        self.records = []
        self.fingerprint = None
        self.embedding_signature = None

    def add_vectors(self, embeddings, records):
        vectors = np.asarray(embeddings, dtype="float32")
        if vectors.shape != (len(records), self.index.d) or not np.isfinite(vectors).all():
            raise ValueError("Invalid embedding matrix")
        if np.any(np.linalg.norm(vectors, axis=1) == 0):
            raise ValueError("Zero embedding")
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        self.records.extend(records)

    def search(self, embedding, k=3):
        if not self.records:
            return []
        query = np.asarray([embedding], dtype="float32")
        if query.shape != (1, self.index.d) or not np.isfinite(query).all() or not np.linalg.norm(query):
            raise ValueError("Invalid query embedding")
        faiss.normalize_L2(query)
        scores, indices = self.index.search(query, min(k, len(self.records)))
        return [(self.records[int(i)], float(score)) for i, score in zip(indices[0], scores[0]) if i >= 0]

    def save(self, directory, fingerprint, embedding_signature=None):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        payload = faiss.serialize_index(self.index).tobytes()
        filename = "faiss_db." + uuid4().hex + ".index"
        target = directory / filename
        target.write_bytes(payload)
        manifest = {"version": 1, "fingerprint": fingerprint, "index": filename,
                    "sha256": sha256(payload).hexdigest(), "records": self.records,
                    "embeddingSignature": embedding_signature}
        temporary = directory / (uuid4().hex + ".json.tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        # Publishing one manifest switches the index and metadata together.
        temporary.replace(directory / "faiss_db.json")
        for old in directory.glob("faiss_db.*.index"):
            if old != target:
                old.unlink(missing_ok=True)

    @classmethod
    def load(cls, directory, fingerprint=None):
        directory = Path(directory)
        manifest = json.loads((directory / "faiss_db.json").read_text(encoding="utf-8"))
        if manifest.get("version") != 1 or (fingerprint is not None and manifest.get("fingerprint") != fingerprint):
            raise ValueError("Stale RAG index")
        filename = manifest["index"]
        if Path(filename).name != filename or not filename.startswith("faiss_db.") or not filename.endswith(".index"):
            raise ValueError("Invalid index filename")
        payload = (directory / filename).read_bytes()
        if sha256(payload).hexdigest() != manifest["sha256"]:
            raise ValueError("Corrupt RAG index")
        index = faiss.deserialize_index(np.frombuffer(payload, dtype="uint8"))
        records = manifest["records"]
        if not isinstance(index, faiss.IndexFlatIP) or index.ntotal != len(records):
            raise ValueError("Index metadata mismatch")
        result = cls(index.d)
        result.index, result.records = index, records
        result.fingerprint = manifest["fingerprint"]
        result.embedding_signature = manifest.get("embeddingSignature")
        return result
