"""Adapt code/RAG to the authenticated application and existing source format."""
from pathlib import Path
import re
import sys
import logging
from fastapi import HTTPException
from .retrieval import Passage
from .conversation_context import topic_lookup

CODE_ROOT = Path(__file__).resolve().parents[2] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))
from RAG.utils import RagConfig, RagRetriever, read_documents  # noqa: E402


class KnowledgeRetriever:
    def __init__(self, settings):
        self.method = "vector"
        self.config = RagConfig(data_path=settings.rag_data_path, persist_dir=settings.rag_persist_dir,
                                model=settings.embedding_model, device=settings.embedding_device,
                                cache_dir=settings.embedding_cache_dir, chunk_size=settings.rag_chunk_size,
                                chunk_overlap=settings.rag_chunk_overlap, top_k=settings.rag_top_k,
                                min_score=settings.rag_min_score, query_cache_size=settings.rag_query_cache_size,
                                cpu_storage=settings.embedding_cpu_storage)
        self.engine = RagRetriever(self.config)

    def warmup(self, documents):
        """Prepare the real vector runtime before the API advertises readiness."""
        corpus = self.documents() + documents
        with self.engine.lock:
            if self.engine.prepare(corpus):
                embedding = self.engine._embedding()
                embedding.embed_query("中药知识库")
                logging.getLogger("uvicorn.error").info("Qwen load timings: %s", getattr(embedding, "load_timings", {}))

    def documents(self):
        try:
            return read_documents(self.config.data_path)
        except (OSError, ValueError):
            raise HTTPException(503, "RAG 资料无法读取，请联系管理员检查 code/data 中的 UTF-8 Markdown。") from None

    def retrieve(self, question, documents, reference):
        try:
            results = self.engine.search(question, documents)
        except (ImportError, OSError, ValueError, RuntimeError):
            raise HTTPException(503, "本地向量检索尚未就绪，请按 docs/RAG.md 安装依赖、下载嵌入模型并构建索引。") from None
        sources = {doc["id"]: doc for doc in documents if not doc.get("demo")}
        topics = topic_lookup(documents, reference)(question)
        passages = []
        for record, _score in results:
            # Explicit herb names restrict other-herb hits; general preparation
            # chapters can still supply relevant processing context.
            if topics and not any(topic in record["text"] for topic in topics):
                processing = re.search(r"炮制|加工|饮片|切制|采收|煎药|煎煮", question)
                general = re.search(r"(?:\d+\.)+\d*\s+.*(?:炮制|方法|煎药)", record["text"])
                if not (processing and general):
                    continue
            doc = sources[record["source_id"]]
            source = {"id": doc["id"], "name": doc["name"], "fullText": doc.get("content", doc.get("fullText", "")),
                      "demo": False, **({"blocks": doc["blocks"]} if doc.get("blocks") else {})}
            passages.append(Passage(source, record["text"].splitlines()[0], record["text"], record["index"]))
        return passages
