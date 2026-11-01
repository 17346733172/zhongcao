"""Markdown loading, heading-aware splitting, index freshness and retrieval."""
from dataclasses import dataclass
from collections import OrderedDict
from hashlib import sha256
import json
from pathlib import Path
import re
from threading import RLock

CODE_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RagConfig:
    data_path: Path = CODE_ROOT / "data"
    persist_dir: Path = CODE_ROOT / "db"
    model: str = "Qwen/Qwen3-Embedding-0.6B"
    device: str = "cpu"
    cache_dir: Path = CODE_ROOT / "models"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 3
    min_score: float = 0.45
    query_cache_size: int = 128
    cpu_storage: str = "bf16"

    def __post_init__(self):
        if not 128 <= self.chunk_size <= 2000 or not 0 <= self.chunk_overlap < self.chunk_size // 2:
            raise ValueError("RAG 分块大小须为 128–2000，重叠小于分块大小的一半")
        if not 1 <= self.top_k <= 3 or not 0 <= self.min_score <= 1:
            raise ValueError("RAG_TOP_K 须为 1–3，RAG_MIN_SCORE 须为 0–1")
        if not 0 <= self.query_cache_size <= 1024:
            raise ValueError("RAG_QUERY_CACHE_SIZE 须为 0–1024")
        if self.cpu_storage not in {"fp32", "bf16"}:
            raise ValueError("EMBEDDING_CPU_STORAGE 须为 fp32 或 bf16")



def markdown_blocks(text):
    blocks = []
    paragraph = []
    table = []

    def flush():
        if paragraph:
            blocks.append({"type": "paragraph", "text": "\n".join(paragraph)})
            paragraph.clear()

    def flush_table():
        if table:
            rows = [[cell.strip().replace("\\|", "|").replace("<br>", "\n")
                     for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
                    for line in table]
            if len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1]):
                blocks.append({"type": "table", "rows": [rows[0], *rows[2:]]})
            else:
                blocks.append({"type": "paragraph", "text": "\n".join(table)})
            table.clear()

    for line in text.splitlines():
        if line.strip().startswith("|"):
            flush()
            table.append(line)
            continue
        flush_table()
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush()
            blocks.append({"type": "heading", "level": min(len(heading[1]), 3), "text": heading[2].strip()})
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
    flush()
    flush_table()
    return blocks


def read_documents(directory):
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError("RAG 数据目录不存在，请检查 RAG_DATA_PATH")
    documents = []
    for file in sorted(root.rglob("*")):
        if file.suffix.lower() not in {".md", ".txt"} or not file.is_file():
            continue
        if not file.resolve().is_relative_to(root):
            raise ValueError("RAG 数据文件不能链接到数据目录以外")
        if file.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("RAG 单份资料不能超过 10 MB")
        text = file.read_text(encoding="utf-8-sig")
        if not text.strip():
            continue
        relative = file.relative_to(root).as_posix()
        documents.append({"id": "rag-" + sha256(relative.encode()).hexdigest()[:20], "name": relative,
                          "content": text, "fullText": text, "blocks": markdown_blocks(text),
                          "status": "ready", "demo": False})
    return documents


def split_markdown(text, chunk_size=500, chunk_overlap=50):
    """Retain heading ancestry; overlap only body text; never produce a zero step."""
    if not 128 <= chunk_size <= 2000 or not 0 <= chunk_overlap < chunk_size // 2:
        raise ValueError("Invalid chunk parameters")
    headings, body, chunks = [], [], []

    def flush():
        content = "\n".join(body).strip()
        if not content:
            return
        # Limit unusual very long headings while leaving room for the body.
        prefix = "\n".join(h[1] for h in headings)[-(chunk_size // 3):]
        prefix = prefix + "\n" if prefix else ""
        available = chunk_size - len(prefix)
        step = available - chunk_overlap
        start = 0
        while start < len(content):
            chunks.append(prefix + content[start:start + available])
            if start + available >= len(content):
                break
            start += step

    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            flush()
            body = []
            level = len(match[1])
            headings = [h for h in headings if h[0] < level] + [(level, match[2].strip())]
        else:
            body.append(line)
    flush()
    return chunks


def valid_query(question):
    # Semantic similarity must not turn numeric/noise input into an herbal hit.
    return bool(re.search(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}", question))


class RagRetriever:
    def __init__(self, config, embedding_factory=None):
        self.config = config
        self.embedding_factory = embedding_factory
        self.embedding = None
        self.store = None
        self.fingerprint = None
        self.embedding_signature = None
        self.query_cache = OrderedDict()
        self.lock = RLock()

    def _embedding(self):
        if self.embedding is None:
            if self.embedding_factory:
                self.embedding = self.embedding_factory()
            else:
                from .Embeddings import QwenEmbedding
                local = self.config.cache_dir / self.config.model.split("/")[-1]
                model = str(local) if (local / "model.safetensors").is_file() else self.config.model
                self.embedding = QwenEmbedding(model, self.config.device,
                                               cache_dir=str(self.config.cache_dir), cpu_storage=self.config.cpu_storage)
        return self.embedding

    def _records(self, documents):
        records = []
        for doc in documents:
            if doc.get("demo") or doc.get("status", "ready") != "ready":
                continue
            for index, chunk in enumerate(split_markdown(doc.get("content", doc.get("fullText", "")),
                                                         self.config.chunk_size, self.config.chunk_overlap)):
                records.append({"source_id": doc["id"], "text": chunk, "index": index})
        return records

    def prepare(self, documents, force=False):
        from .faiss_db import FaissVectorStore
        records = self._records(documents)
        signature = {"pipeline": "qwen3-last-token-query-instruction-v1", "model": self.config.model,
                     "chunk_size": self.config.chunk_size, "overlap": self.config.chunk_overlap}
        model_dir = Path(self.config.model)
        local_dir = self.config.cache_dir / self.config.model.split("/")[-1]
        if not model_dir.is_dir() and (local_dir / "model.safetensors").is_file():
            model_dir = local_dir
        if model_dir.is_dir():
            signature["model_files"] = [(p.name, p.stat().st_size, p.stat().st_mtime_ns)
                                         for p in sorted(model_dir.iterdir()) if p.is_file()]
        embedding_signature = sha256(json.dumps(signature, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        fingerprint = sha256(json.dumps([embedding_signature, records], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        with self.lock:
            if self.embedding_signature is not None and self.embedding_signature != embedding_signature:
                self.embedding = None
                self.query_cache.clear()
            self.embedding_signature = embedding_signature
            if not force and fingerprint == self.fingerprint:
                return len(records)
            if not records:
                self.store, self.fingerprint = None, fingerprint
                return 0
            previous = None
            if not force:
                try:
                    previous = FaissVectorStore.load(self.config.persist_dir)
                    if previous.fingerprint == fingerprint:
                        self.store = previous
                        self.fingerprint = fingerprint
                        return len(records)
                except (OSError, ValueError, KeyError, TypeError, RuntimeError):
                    pass
            cache = {}
            if previous is not None and previous.embedding_signature == embedding_signature:
                cache = {record["text"]: previous.index.reconstruct(i).tolist()
                         for i, record in enumerate(previous.records)}
            missing = list(dict.fromkeys(record["text"] for record in records if record["text"] not in cache))
            if missing:
                cache.update(zip(missing, self._embedding().get_embeddings(missing), strict=True))
            embeddings = [cache[record["text"]] for record in records]
            store = FaissVectorStore(len(embeddings[0]))
            store.add_vectors(embeddings, records)
            store.save(self.config.persist_dir, fingerprint, embedding_signature)
            self.store, self.fingerprint = store, fingerprint
            return len(records)

    def search(self, question, documents):
        if not valid_query(question):
            return []
        with self.lock:
            self.prepare(documents)
            if self.store is None:
                return []
            query_vector = self.query_cache.get(question)
            if query_vector is None:
                query_vector = self._embedding().embed_query(question)
            results = self.store.search(query_vector, self.config.top_k)
            # Cache only validated vectors; failed model/search output must not
            # poison subsequent attempts. Results are always searched afresh.
            if self.config.query_cache_size:
                self.query_cache[question] = query_vector
                self.query_cache.move_to_end(question)
                while len(self.query_cache) > self.config.query_cache_size:
                    self.query_cache.popitem(last=False)
            return [(record, score) for record, score in results if score >= self.config.min_score]
