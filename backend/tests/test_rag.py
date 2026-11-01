from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import secrets
import sys
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.security import hash_password
from app.rag import KnowledgeRetriever
from RAG.utils import RagConfig, RagRetriever, read_documents, split_markdown, markdown_blocks
from RAG.faiss_db import FaissVectorStore


class TinyEmbedding:
    """Controlled vectors test ranking and wiring; real Qwen is tested separately."""
    def __init__(self):
        self.calls = 0

    def get_embeddings(self, texts):
        self.calls += 1
        return [[1., 0., 0.] if "陈皮" in text else [0., 1., 0.] for text in texts]

    def embed_query(self, text):
        return [1., 0., 0.] if "胸口" in text or "陈皮" in text else [0., 0., 1.]


class RagTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.config = RagConfig(data_path=self.data, persist_dir=self.root / "db", min_score=.45)
        self.embed = TinyEmbedding()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        (self.data / name).write_text(text, encoding="utf-8")

    def engine(self, config=None):
        return RagRetriever(config or self.config, lambda: self.embed)

    def test_markdown_nested_headings_overlap_and_limits(self):
        body = "甲乙丙丁戊己庚辛壬癸" * 100
        chunks = split_markdown("# 总论\n## 陈皮\n" + body, 200, 30)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(c.startswith("总论\n陈皮\n") and len(c) <= 200 for c in chunks))
        text = chunks[0][len("总论\n陈皮\n"):]
        for chunk in chunks[1:]:
            next_text = chunk[len("总论\n陈皮\n"):]
            self.assertEqual(text[-30:], next_text[:30])
            text += next_text[30:]
        self.assertEqual(text, body)
        with self.assertRaises(ValueError):
            split_markdown(body, 200, 200)
        self.assertTrue(all(len(c) <= 200 for c in split_markdown("# " + "长" * 1000 + "\n正文" * 200, 200, 30)))

    def test_reader_recurses_and_excludes_original_pdf_and_json(self):
        (self.data / "nested").mkdir()
        self.write("nested/herb.MD", "# 陈皮\n【功效】理气健脾。")
        self.write("empty.md", "  ")
        self.write("source.pdf", "not markdown")
        self.write("source.json", "{}")
        docs = read_documents(self.data)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["name"], "nested/herb.MD")
        self.assertEqual(docs[0]["blocks"][0]["text"], "陈皮")

    def test_markdown_tables_preserve_cells_for_source_view(self):
        blocks = markdown_blocks("#### 特殊煎法\n\n| 药物 | 说明 |\n| --- | --- |\n| 甲\\|乙 | 先煎<br>复核 |\n\n正文")
        self.assertEqual(blocks[0]["level"], 3)
        self.assertEqual(blocks[1], {"type": "table", "rows": [["药物", "说明"], ["甲|乙", "先煎\n复核"]]})
        self.assertEqual(blocks[2]["text"], "正文")

    def test_upload_and_delete_only_embed_new_chunks(self):
        self.write("a.md", "# 陈皮\n原有正文。")
        engine = self.engine()
        engine.prepare(read_documents(self.data))
        with patch.object(self.embed, "get_embeddings", wraps=self.embed.get_embeddings) as generate:
            self.write("b.md", "# 人参\n新增正文。")
            engine.prepare(read_documents(self.data))
            self.assertEqual(len(generate.call_args.args[0]), 1)
            self.assertIn("人参", generate.call_args.args[0][0])
            (self.data / "b.md").unlink()
            engine.prepare(read_documents(self.data))
            self.assertEqual(generate.call_count, 1)
            self.assertEqual(len(engine.store.records), 1)

    def test_semantic_retrieval_threshold_and_noise(self):
        self.write("陈皮.md", "# 陈皮\n理气健脾，燥湿化痰。")
        self.write("人参.md", "# 人参\n大补元气。")
        engine = self.engine()
        self.assertEqual(engine.search("111", read_documents(self.data)), [])
        self.assertEqual(self.embed.calls, 0)
        results = engine.search("胸口痞闷怎么办", read_documents(self.data))
        self.assertEqual(len(results), 1)
        self.assertIn("陈皮", results[0][0]["text"])
        self.assertEqual(engine.search("天文学", read_documents(self.data)), [])

    def test_persistence_reuses_index_and_changes_or_deletions_rebuild(self):
        self.write("a.md", "# 陈皮\n原始资料。")
        docs = read_documents(self.data)
        self.engine().prepare(docs)
        self.assertEqual(self.embed.calls, 1)
        reloaded = self.engine()
        reloaded.prepare(docs)
        self.assertEqual(self.embed.calls, 1)
        self.assertIsNone(reloaded.embedding, "加载现有索引不应提前加载 Qwen")
        self.write("a.md", "# 陈皮\n更新后的资料。")
        reloaded.prepare(read_documents(self.data))
        self.assertEqual(self.embed.calls, 2)
        self.assertIn("更新后", reloaded.store.records[0]["text"])
        (self.data / "a.md").unlink()
        self.assertEqual(reloaded.search("陈皮", read_documents(self.data)), [])
        # A new process must also see the empty current corpus, never old chunks.
        self.assertEqual(self.engine().search("陈皮", []), [])

    def test_model_chunk_changes_and_corrupt_index_invalidate_cache(self):
        self.write("a.md", "# 陈皮\n资料。")
        docs = read_documents(self.data)
        self.engine().prepare(docs)
        self.engine(replace(self.config, model="different-model")).prepare(docs)
        self.assertEqual(self.embed.calls, 2)
        changed = replace(self.config, model="different-model", chunk_size=300)
        self.engine(changed).prepare(docs)
        self.assertEqual(self.embed.calls, 3)
        manifest = json.loads((self.config.persist_dir / "faiss_db.json").read_text(encoding="utf-8"))
        (self.config.persist_dir / manifest["index"]).write_bytes(b"corrupt")
        self.engine(changed).prepare(docs)
        self.assertEqual(self.embed.calls, 4)
        self.assertEqual(len(list(self.config.persist_dir.glob("*.index"))), 1)
        self.assertFalse(list(self.config.persist_dir.glob("*.pkl")))

    def test_vectors_are_normalized_and_metadata_corruption_rejected(self):
        store = FaissVectorStore(2)
        store.add_vectors([[2, 0], [0, 3]], [{"text": "A"}, {"text": "B"}])
        self.assertAlmostEqual(store.search([5, 0], 1)[0][1], 1)
        with self.assertRaises(ValueError):
            store.add_vectors([[0, 0]], [{"text": "zero"}])
        store.save(self.config.persist_dir, "fp")
        manifest_path = self.config.persist_dir / "faiss_db.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["records"] = []
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError):
            FaissVectorStore.load(self.config.persist_dir, "fp")

    def test_authenticated_chat_uses_markdown_semantics_and_general_stays_isolated(self):
        self.write("中药.md", "# 陈皮\n【功效】理气健脾，燥湿化痰。")
        password = secrets.token_urlsafe(18)
        settings = Settings(database=self.root / "app.db", rag_data_path=self.data,
                            rag_persist_dir=self.config.persist_dir, deepseek_api_key="test-only")
        app = create_app(settings)
        app.state.rag.engine = self.engine()
        headers = {"X-CSRF-Protection": "1"}
        with TestClient(app, headers=headers) as client:
            self.assertEqual(client.post("/api/chat", json={"question": "陈皮", "use_knowledge": True}).status_code, 401)
            with app.state.database.connect() as db:
                db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                           ("viewer", "读者", hash_password(password), "viewer", int(time.time())))
            client.post("/api/auth/login", json={"username": "viewer", "password": password})
            self.assertEqual(client.post("/api/chat", json={"question": "陈皮", "use_knowledge": True},
                                         headers={"X-CSRF-Protection": ""}).status_code, 403)
            from app.chat import GeneratedAnswer
            body = GeneratedAnswer.model_validate({"answerable": True, "title": "资料回答", "sections": [
                {"title": "要点", "content": "理气健脾。", "origin": "document", "citations": [1]}]})
            with patch("app.chat.request_completion", return_value=body) as generate:
                response = client.post("/api/chat", json={"question": "胸口痞闷怎么办", "use_knowledge": True})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["sources"][0]["name"], "中药.md")
                self.assertEqual(response.json()["retrievalMethod"], "vector")
                self.assertIn("retrieval;dur=", response.headers["server-timing"])
                self.assertIn("generation;dur=", response.headers["server-timing"])
                self.assertIn("total;dur=", response.headers["server-timing"])
                self.assertNotIn("test-only", response.headers["server-timing"])
                self.assertIn("陈皮", generate.call_args.args[1][0]["text"])
                self.assertNotIn(".docx", json.dumps(generate.call_args.args[1]))
            with patch.object(app.state.rag, "documents", side_effect=AssertionError("不能读取 Markdown")), \
                    patch("app.chat.request_json", return_value=json.dumps({"title": "普通回答", "sections": [{"title": "要点", "content": "普通知识。"}]})):
                response = client.post("/api/chat", json={"question": "陈皮", "use_knowledge": False})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["sources"], [])

    def test_missing_model_is_reported_without_paths_or_key(self):
        retriever = KnowledgeRetriever(Settings(rag_data_path=self.data))
        with patch.object(retriever.engine, "search", side_effect=OSError("private-key /secret/model")):
            with self.assertRaises(Exception) as error:
                retriever.retrieve("陈皮", [], None)
        self.assertEqual(error.exception.status_code, 503)
        self.assertNotIn("private-key", error.exception.detail)

    def test_explicit_herb_excludes_other_herbs_but_keeps_general_processing(self):
        retriever = KnowledgeRetriever(Settings(rag_data_path=self.data))
        documents = [{"id": "a", "name": "中药.md", "content": "# 黄芪\n原文", "blocks": markdown_blocks("# 黄芪\n原文")}]
        hits = [({"source_id": "a", "index": i, "text": text}, .7) for i, text in enumerate(
            ["黄芪\n补气", "3.3.2 炮制的方法\n切制", "黄柏\n清热"]) ]
        with patch.object(retriever.engine, "search", return_value=hits):
            self.assertEqual(len(retriever.retrieve("黄芪怎么炮制成饮片", documents, None)), 2)

    def test_semantic_hit_does_not_bypass_colloquial_follow_up_understanding(self):
        from app.chat import ChatService, GeneratedAnswer
        from app.conversation_context import Resolution
        from app.retrieval import Passage
        source = {"id": "a", "name": "中药.md", "fullText": "陈皮", "blocks": markdown_blocks("# 陈皮\n【使用注意】慎用。")}
        doc = {**source, "content": source["fullText"]}
        retriever = KnowledgeRetriever(Settings(rag_data_path=self.data))
        service = ChatService(Settings(deepseek_api_key="test-only"), retriever)
        generated = GeneratedAnswer.model_validate({"answerable": True, "title": "注意", "sections": [
            {"title": "注意", "content": "慎用。", "origin": "document", "citations": [1]}]})
        with patch.object(retriever, "retrieve", return_value=[Passage(source, "陈皮", "陈皮\n【使用注意】慎用。", 0)]) as retrieve_call, \
                patch("app.chat.request_understanding", return_value=Resolution("陈皮的不良反应和禁忌")) as understand, \
                patch("app.chat.request_completion", return_value=generated):
            answer = service.answer("有什么不要的药效吗", [doc], None, [{"question": "陈皮", "answer": "功效"}])
            understand.assert_called_once()
            retrieve_call.assert_called_once_with("陈皮的不良反应和禁忌", [doc], None)
            self.assertEqual(answer["resolvedQuestion"], "陈皮的不良反应和禁忌")

    def test_query_vector_lru_reuses_embedding_and_refreshes_documents(self):
        self.write("a.md", "# 陈皮\n原始正文。")
        engine = self.engine(replace(self.config, query_cache_size=1))
        with patch.object(self.embed, "embed_query", wraps=self.embed.embed_query) as embed:
            engine.search("陈皮功效", read_documents(self.data))
            engine.search("陈皮功效", read_documents(self.data))
            self.assertEqual(embed.call_count, 1)
            self.write("a.md", "# 陈皮\n更新正文。")
            found = engine.search("陈皮功效", read_documents(self.data))
            self.assertIn("更新正文", found[0][0]["text"])
            self.assertEqual(embed.call_count, 1, "资料变化应重查新索引，但不必重算相同查询向量")
            engine.search("另一个问题", read_documents(self.data))
            engine.search("陈皮功效", read_documents(self.data))
            self.assertEqual(embed.call_count, 3)
            engine.config = replace(engine.config, model="new-model")
            engine.search("陈皮功效", read_documents(self.data))
            self.assertEqual(embed.call_count, 4)

    def test_query_cache_can_be_disabled_and_does_not_store_failed_embeddings(self):
        self.write("a.md", "# 陈皮\n正文。")
        engine = self.engine(replace(self.config, query_cache_size=0))
        with patch.object(self.embed, "embed_query", wraps=self.embed.embed_query) as embed:
            for _ in range(2):
                engine.search("陈皮", read_documents(self.data))
            self.assertEqual(embed.call_count, 2)
            self.assertFalse(engine.query_cache)
        engine = self.engine()
        with patch.object(self.embed, "embed_query", side_effect=RuntimeError("local failure")):
            with self.assertRaises(RuntimeError):
                engine.search("陈皮", read_documents(self.data))
        self.assertFalse(engine.query_cache)

    def test_validated_answer_cache_is_scoped_expires_and_invalidates_on_source_edits(self):
        from app.chat import ChatService, GeneratedAnswer
        from app.retrieval import Passage
        source = {"id": "a", "name": "中药.md", "fullText": "陈皮原文"}
        retriever = KnowledgeRetriever(Settings(rag_data_path=self.data))
        service = ChatService(Settings(deepseek_api_key="test-only"), retriever)
        generated = GeneratedAnswer.model_validate({"answerable": True, "title": "资料回答", "sections": [
            {"title": "要点", "content": "原文支持的回答。", "origin": "document", "citations": [1]}]})
        clock = [0.0]
        with patch("app.chat.perf_counter", side_effect=lambda: clock[0]), \
                patch.object(retriever, "retrieve", side_effect=lambda *args: [Passage(source, "陈皮", "陈皮\n【功效】理气。", 0)]), \
                patch("app.chat.request_completion", return_value=generated) as generate:
            first = service.answer("陈皮", [], None, cache_scope="alice")
            clock[0] = 119
            timings = {}
            cached = service.answer("陈皮", [], None, timings=timings, cache_scope="alice")
            self.assertEqual(generate.call_count, 1)
            self.assertEqual(first, cached)
            self.assertIn("answer_cache", timings)
            clock[0] = 121
            service.answer("陈皮", [], None, cache_scope="alice")
            self.assertEqual(generate.call_count, 2, "缓存命中不能延长原始存活时间")
            service.answer("陈皮", [], None, cache_scope="bob")
            self.assertEqual(generate.call_count, 3, "不同账号不能复用回答")
            source["fullText"] = "陈皮原文更新：修改了未聚焦的字段"
            service.answer("陈皮", [], None, cache_scope="alice")
            self.assertEqual(generate.call_count, 4, "即使聚焦片段相同，完整原文变化也应使回答缓存失效")

    def test_invalid_answer_is_not_cached(self):
        from app.chat import ChatService, GeneratedAnswer
        from app.retrieval import Passage
        source = {"id": "a", "name": "中药.md", "fullText": "陈皮原文"}
        retriever = KnowledgeRetriever(Settings(rag_data_path=self.data))
        service = ChatService(Settings(deepseek_api_key="test-only"), retriever)
        invalid = GeneratedAnswer.model_validate({"answerable": True, "title": "资料回答", "sections": [
            {"title": "要点", "content": "无效引用。", "origin": "document", "citations": [99]}]})
        with patch.object(retriever, "retrieve", return_value=[Passage(source, "陈皮", "陈皮原文", 0)]), \
                patch("app.chat.request_completion", return_value=invalid) as generate:
            for _ in range(2):
                with self.assertRaises(Exception) as error:
                    service.answer("陈皮", [], None, cache_scope="alice")
                self.assertEqual(error.exception.status_code, 502)
            self.assertEqual(generate.call_count, 2)
            self.assertFalse(service.answer_cache)


if __name__ == "__main__":
    unittest.main()
