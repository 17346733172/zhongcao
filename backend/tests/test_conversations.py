from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import secrets
from tempfile import TemporaryDirectory
import time
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.security import hash_password

HEADERS = {"X-CSRF-Protection": "1", "Origin": "http://127.0.0.1:3000"}


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.settings = Settings(rag_enabled=False, database=Path(self.temp.name) / "test.db")
        self.app = create_app(self.settings)
        self.client = TestClient(self.app, headers=HEADERS)
        self.client.__enter__()
        self.password = secrets.token_urlsafe(18)
        with self.app.state.database.connect() as db:
            for name, role in [("alice", "viewer"), ("bob", "admin")]:
                db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                           (name, name, hash_password(self.password), role, int(time.time())))
        self.identifier = str(uuid4())
        self.endpoint = f"/api/conversations/{self.identifier}/messages"

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def login(self, username="alice", client=None):
        response = (client or self.client).post("/api/auth/login", json={"username": username, "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)

    def payload(self, question="陈皮有什么作用？"):
        return {"libraryId": "herbal", "message": {
            "id": str(uuid4()), "question": question, "time": "今天 15:00", "answeredAt": "2026-11-19T07:00:00Z",
            "answer": {"title": "陈皮", "introduction": "引用原文", "sections": [{"title": "资料", "content": "原文[1]", "sourceIndices": [0]}],
                       "sources": [{"id": "qa", "name": "测试原文", "excerpt": "原文", "fullText": "完整原文", "demo": False}],
                       "mode": "generated", "resolvedQuestion": question,
                       "toolCalls": [{"name": "herbal_reference", "title": "基础资料", "action": "query", "status": "success", "durationMs": 1}],
                       "charts": [{"title": "真实字段模拟", "unit": "个", "categories": ["完成"], "series": [{"name": "批次", "values": [2]}]}],
                       "usage": {"inputTokens": 12, "outputTokens": 7, "scope": "tool_selection"}}, "showSources": True}}

    def test_auth_csrf_and_private_ownership(self):
        self.assertEqual(self.client.get("/api/conversations").status_code, 401)
        self.assertEqual(self.client.post(self.endpoint, json=self.payload()).status_code, 401)
        self.login()
        payload = self.payload()
        self.assertEqual(self.client.post(self.endpoint, json=payload, headers={"X-CSRF-Protection": ""}).status_code, 403)
        self.assertEqual(self.client.post(self.endpoint, json=payload).status_code, 200)
        self.login("bob")
        self.assertEqual(self.client.get("/api/conversations").json(), [])
        self.assertEqual(self.client.get(f"/api/conversations/{self.identifier}").status_code, 404)
        # Even guessing another account's conversation and message UUID cannot overwrite it.
        other = self.payload("Bob 的会话")
        other["message"]["id"] = payload["message"]["id"]
        self.assertEqual(self.client.post(self.endpoint, json=other).status_code, 200)
        self.login()
        self.assertEqual(self.client.get(f"/api/conversations/{self.identifier}").json()["messages"][0]["question"], payload["message"]["question"])

    def test_full_message_roundtrip_and_restart(self):
        self.login()
        payload = self.payload()
        reference = json.loads((Path(__file__).resolve().parents[1] / "resources/herbal-reference.json").read_text(encoding="utf-8"))
        payload["message"]["answer"]["sources"] = [reference]
        payload["message"]["originalAnswer"] = deepcopy(payload["message"]["answer"])
        saved = self.client.post(self.endpoint, json=payload)
        self.assertEqual(saved.status_code, 200, saved.text)
        summaries = self.client.get("/api/conversations")
        self.assertEqual(summaries.headers["cache-control"], "no-store")
        self.assertEqual(summaries.json()[0]["messages"], [])
        self.assertEqual(summaries.json()[0]["messageCount"], 1)
        with TestClient(create_app(self.settings), headers=HEADERS) as restarted:
            self.login(client=restarted)
            result = restarted.get(f"/api/conversations/{self.identifier}").json()
            self.assertEqual(result["messages"][0], payload["message"])
            self.assertTrue(result["messagesLoaded"])

    def test_retry_is_idempotent_and_changed_replay_is_rejected(self):
        self.login()
        payload = self.payload()
        for _ in range(2):
            self.assertEqual(self.client.post(self.endpoint, json=payload).status_code, 200)
        changed = deepcopy(payload)
        changed["message"]["question"] = "不得覆盖"
        self.assertEqual(self.client.post(self.endpoint, json=changed).status_code, 409)
        result = self.client.get(f"/api/conversations/{self.identifier}").json()
        self.assertEqual(result["messageCount"], 1)
        self.assertEqual(result["messages"][0]["question"], payload["message"]["question"])

    def test_concurrent_tabs_append_without_losing_messages(self):
        self.login()
        items = [self.payload(f"并发问题 {index}") for index in range(8)]
        with ThreadPoolExecutor(max_workers=4) as executor:
            statuses = list(executor.map(lambda payload: self.client.post(self.endpoint, json=payload).status_code, items))
        self.assertEqual(statuses, [200] * 8)
        messages = self.client.get(f"/api/conversations/{self.identifier}").json()["messages"]
        self.assertEqual({item["id"] for item in messages}, {item["message"]["id"] for item in items})

    def test_invalid_input_and_request_limit_do_not_save(self):
        self.login()
        for field, value in [("question", ""), ("id", "invalid"), ("answeredAt", "2026-11-19T15:00:00"), ("answer", {"sections": "broken"})]:
            payload = self.payload()
            payload["message"][field] = value
            response = self.client.post(self.endpoint, json=payload)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("broken", response.text)
        payload = self.payload()
        payload["user_id"] = 2
        self.assertEqual(self.client.post(self.endpoint, json=payload).status_code, 422)
        payload = self.payload()
        payload["message"]["answer"]["introduction"] = "x" * (8 * 1024 * 1024)
        self.assertEqual(self.client.post(self.endpoint, json=payload).status_code, 413)
        self.assertEqual(self.client.get("/api/conversations").json(), [])

    def test_recent_order_and_first_title_are_preserved(self):
        self.login()
        self.client.post(self.endpoint, json=self.payload("第一个问题"))
        second = str(uuid4())
        self.client.post(f"/api/conversations/{second}/messages", json=self.payload("另一个会话"))
        self.assertEqual(self.client.get("/api/conversations").json()[0]["id"], second)
        self.client.post(self.endpoint, json=self.payload("继续第一个"))
        self.assertEqual(self.client.get("/api/conversations").json()[0]["title"], "第一个问题")
        self.assertEqual(self.client.get("/api/conversations").json()[0]["messageCount"], 2)


if __name__ == "__main__":
    unittest.main()
