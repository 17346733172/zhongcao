from pathlib import Path
from tempfile import TemporaryDirectory
import secrets
import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from unittest.mock import patch
import time
import unittest
from fastapi.testclient import TestClient
from app.config import Settings
from app.database import Database
from app.main import create_app
from app.security import hash_password, token_hash

HEADERS = {"X-CSRF-Protection": "1", "Origin": "http://127.0.0.1:3000"}


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.settings = Settings(database=Path(self.temp.name) / "test.db")
        self.app = create_app(self.settings)
        self.db = self.app.state.database
        self.password = secrets.token_urlsafe(18)
        self.client = TestClient(self.app, headers=HEADERS)
        self.client.__enter__()
        with self.db.connect() as db:
            for role in ("admin", "editor", "viewer"):
                db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                           (role, role, hash_password(self.password), role, int(time.time())))

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def login(self, role="admin", client=None):
        response = (client or self.client).post("/api/auth/login", json={"username": role, "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def test_anonymous_denied_and_health_available(self):
        self.assertEqual(self.client.get("/api/health").json()["status"], "ok")
        for path in ("/api/auth/me", "/api/users", "/api/documents"):
            self.assertEqual(self.client.get(path).status_code, 401)

    def test_login_cookie_hash_and_logout_revocation(self):
        response = self.login()
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)
        self.assertIn("max-age=28800", cookie)
        self.assertNotIn("password_hash", response.text)
        token = self.client.cookies[self.settings.cookie_name]
        with self.db.connect() as db:
            stored = db.execute("SELECT token_hash FROM sessions").fetchone()[0]
            password = db.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()[0]
        self.assertEqual(stored, token_hash(token))
        self.assertNotEqual(stored, token)
        self.assertTrue(password.startswith("$argon2id$"))
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 204)
        self.client.cookies.set(self.settings.cookie_name, token)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_secure_cookie_config(self):
        app = create_app(Settings(database=Path(self.temp.name) / "secure.db", secure_cookie=True))
        with TestClient(app, headers=HEADERS, base_url="https://testserver") as client:
            with app.state.database.connect() as db:
                db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                           ("admin", "Admin", hash_password(self.password), "admin", int(time.time())))
            response = client.post("/api/auth/login", json={"username": "admin", "password": self.password})
            self.assertEqual(response.status_code, 200)
            self.assertIn("Secure", response.headers["set-cookie"])

    def test_rate_limit_and_uniform_login_errors(self):
        for _ in range(8):
            response = self.client.post("/api/auth/login", json={"username": "unknown", "password": "incorrect"})
            self.assertEqual(response.status_code, 401)
        response = self.client.post("/api/auth/login", json={"username": "unknown", "password": "incorrect"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "300")
        self.assertNotIn("incorrect", response.text)

    def test_csrf_and_foreign_origins_denied(self):
        for headers in ({"X-CSRF-Protection": ""}, {"Origin": "https://foreign.example"}):
            self.assertEqual(self.client.post("/api/auth/login", json={"username": "admin", "password": self.password}, headers=headers).status_code, 403)

    def test_viewer_cannot_write_or_manage_users(self):
        self.login("viewer")
        self.assertEqual(self.client.get("/api/documents").status_code, 200)
        self.assertEqual(self.client.get("/api/users").status_code, 403)
        self.assertEqual(self.client.post("/api/users", json={"username": "hacker", "display_name": "X", "password": self.password, "role": "admin"}).status_code, 403)
        self.assertEqual(self.client.post("/api/documents", json={"name": "a.txt", "content": "原文"}).status_code, 403)
        self.assertEqual(self.client.delete("/api/documents/unknown").status_code, 403)
        self.assertEqual(self.client.patch("/api/users/1", json={"role": "viewer", "active": False}).status_code, 403)
        self.assertEqual(self.client.post("/api/users/1/password", json={"password": self.password}).status_code, 403)

    def test_editor_documents_persist_and_are_shared(self):
        self.login("editor")
        self.assertEqual(self.client.get("/api/users").status_code, 403)
        created = self.client.post("/api/documents", json={"name": "资料.md", "content": "# 保留的原文\n核对文本"})
        self.assertEqual(created.status_code, 201)
        document_id = created.json()["id"]
        self.assertTrue(created.json()["stored"])
        # A new app instance must read the same SQLite file.
        with TestClient(create_app(self.settings), headers=HEADERS) as other:
            self.login("viewer", other)
            self.assertEqual(other.get("/api/documents").json()[0]["content"], "# 保留的原文\n核对文本")
            self.assertEqual(other.delete(f"/api/documents/{document_id}").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/documents/{document_id}").status_code, 204)
        self.assertEqual(self.client.get("/api/documents").json(), [])

    def test_create_duplicate_validation_and_no_privilege_in_login(self):
        self.login()
        payload = {"username": "New_User", "display_name": "新用户", "password": self.password, "role": "editor"}
        self.assertEqual(self.client.post("/api/users", json=payload).status_code, 201)
        self.assertEqual(self.client.post("/api/users", json={**payload, "username": "new_user"}).status_code, 409)
        response = self.client.post("/api/users", json={**payload, "username": "bad", "password": "short"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('"short"', response.text)
        self.assertEqual(self.client.post("/api/auth/login", json={"username": "viewer", "password": self.password, "role": "admin"}).status_code, 422)

    def test_role_changes_and_disable_revoke_existing_sessions(self):
        self.login()
        with TestClient(self.app, headers=HEADERS) as other:
            self.login("editor", other)
            self.assertEqual(self.client.patch("/api/users/2", json={"role": "viewer", "active": True}).status_code, 200)
            self.assertEqual(other.get("/api/auth/me").status_code, 401)
            self.login("editor", other)
            self.assertEqual(other.post("/api/documents", json={"name": "a.txt", "content": "内容"}).status_code, 403)
            self.assertEqual(self.client.patch("/api/users/2", json={"role": "viewer", "active": False}).status_code, 200)
            self.assertEqual(other.get("/api/auth/me").status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"username": "editor", "password": self.password}).status_code, 401)
            self.assertEqual(self.client.patch("/api/users/2", json={"role": "editor", "active": True}).status_code, 200)
            self.login("editor", other)

    def test_self_protection_password_change_and_reset(self):
        self.login()
        self.assertEqual(self.client.patch("/api/users/1", json={"role": "viewer", "active": False}).status_code, 400)
        with TestClient(self.app, headers=HEADERS) as other:
            self.login("viewer", other)
            replacement = secrets.token_urlsafe(18)
            self.assertEqual(self.client.post("/api/users/3/password", json={"password": replacement}).status_code, 204)
            self.assertEqual(other.get("/api/auth/me").status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"username": "viewer", "password": self.password}).status_code, 401)
            self.assertEqual(other.post("/api/auth/login", json={"username": "viewer", "password": replacement}).status_code, 200)
            self.assertEqual(other.post("/api/auth/password", json={"current_password": "bad", "password": self.password}).status_code, 400)
            self.assertEqual(other.post("/api/auth/password", json={"current_password": replacement, "password": self.password}).status_code, 204)
            self.assertEqual(other.get("/api/auth/me").status_code, 401)
            self.login("viewer", other)

    def test_expired_and_tampered_sessions_denied(self):
        self.login()
        with self.db.connect() as db:
            db.execute("UPDATE sessions SET expires_at = 0")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.client.cookies.clear()
        self.client.cookies.set(self.settings.cookie_name, "forged-session")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_concurrent_admin_changes_preserve_an_active_admin(self):
        self.login()
        with self.db.connect() as db:
            cursor = db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                                ("second_admin", "Second", hash_password(self.password), "admin", int(time.time())))
            other_id = cursor.lastrowid
        with TestClient(self.app, headers=HEADERS) as other:
            self.login("second_admin", other)
            def disable(client, target):
                return client.patch(f"/api/users/{target}", json={"role": "viewer", "active": False}).status_code
            with ThreadPoolExecutor(max_workers=2) as executor:
                a = executor.submit(disable, self.client, other_id)
                b = executor.submit(disable, other, 1)
                statuses = [a.result(), b.result()]
        self.assertEqual(statuses.count(200), 1)
        self.assertTrue(all(status in {200, 400, 401, 403} for status in statuses))
        with self.db.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1").fetchone()[0], 1)

    def test_first_admin_cli_uses_input_and_never_prints_password(self):
        from app.cli import main
        path = Path(self.temp.name) / "cli.db"
        output = io.StringIO()
        with patch.dict(os.environ, {"DATABASE_PATH": str(path)}), patch.object(sys, "argv", ["cli", "create-admin"]):
            with patch("builtins.input", side_effect=["owner", "Owner"]), patch("app.cli.getpass", side_effect=[self.password, self.password]), redirect_stdout(output):
                main()
            with self.assertRaises(SystemExit) as result, redirect_stdout(output):
                main()
            self.assertEqual(result.exception.code, 1)
        self.assertNotIn(self.password, output.getvalue())
        with Database(path).connect() as db:
            row = db.execute("SELECT username,role,password_hash FROM users").fetchone()
            self.assertEqual((row["username"], row["role"]), ("owner", "admin"))
            self.assertTrue(row["password_hash"].startswith("$argon2id$"))

    def test_text_document_input_boundaries(self):
        self.login("editor")
        for name, content in (("test.pdf", "x"), ("../bad.txt", "x"), ("test.txt", " "), ("test.txt", "字" * 3500000)):
            self.assertEqual(self.client.post("/api/documents", json={"name": name, "content": content}).status_code, 422)
        self.assertEqual(self.client.post("/api/users", content=b"x" * 17000).status_code, 413)
        self.assertEqual(self.client.post("/api/documents", content=b"x" * (12 * 1024 * 1024 + 1)).status_code, 413)
        self.assertEqual(self.client.post("/api/documents", json={"name": "原文.txt", "content": "\ufeff原文"}).json()["content"], "原文")


if __name__ == "__main__":
    unittest.main()
