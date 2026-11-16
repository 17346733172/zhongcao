import asyncio
import json
from pathlib import Path
import secrets
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.security import token_hash
from app.simulation_operations import simulation_request


class SimulationOperationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.settings = Settings(rag_enabled=False, database=Path(self.temp.name) / "test.db",
                                 decoction_base_url="https://simulation.example", decoction_api_key="secret-key",
                                 decoction_http_username="gateway-user", decoction_http_password="gateway-secret",
                                 decoction_proxy_url="http://127.0.0.1:9876")
        self.app = create_app(self.settings)
        self.client = TestClient(self.app).__enter__()
        self.headers = {"X-CSRF-Protection": "1"}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def login(self, role="viewer"):
        token = secrets.token_urlsafe(24)
        with self.app.state.database.connect() as db:
            cursor = db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                                (role, role, "unused", role, int(time.time())))
            db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_hash(token), cursor.lastrowid, time.time() + 600))
        self.client.cookies.set(self.settings.cookie_name, token)

    @patch("app.simulation_operations.simulation_request", new_callable=AsyncMock)
    def test_auth_and_csrf_prevent_platform_access(self, request):
        self.assertEqual(self.client.get("/api/simulation/status").status_code, 401)
        for action in ("scenarios", "start", "pause"):
            self.assertEqual(self.client.post(f"/api/simulation/{action}", json={"count": 1}, headers=self.headers).status_code, 401)
        self.login()
        for action in ("scenarios", "start", "pause"):
            self.assertEqual(self.client.post(f"/api/simulation/{action}", json={"count": 1}).status_code, 403)
            self.assertEqual(self.client.post(f"/api/simulation/{action}", headers={**self.headers, "Origin": "https://untrusted.example"}, json={"count": 1}).status_code, 403)
        request.assert_not_called()

    @patch("app.simulation_operations.simulation_request", new_callable=AsyncMock)
    def test_invalid_count_never_reaches_platform(self, request):
        self.login()
        for body in ({}, {"count": 0}, {"count": 51}, {"count": 1.5}, {"count": "5"}, {"count": True}, {"count": 5, "speed": 10}):
            with self.subTest(body=body):
                response = self.client.post("/api/simulation/scenarios", json=body, headers=self.headers)
                self.assertEqual(response.status_code, 422)
                self.assertIn("1–50", response.json()["detail"])
        request.assert_not_called()

    @patch("app.simulation_operations.simulation_request", new_callable=AsyncMock)
    def test_all_roles_can_generate_requested_count_and_control_clock(self, request):
        for role in ("viewer", "editor", "admin"):
            self.login(role)
            for count in (1, 50):
                ids = [f"batch-{number}" for number in range(count)]
                request.return_value = httpx.Response(201, json={"count": count, "batch_ids": ids})
                with patch.object(self.app.state.data_center_reader, "request_refresh") as refresh:
                    response = self.client.post("/api/simulation/scenarios", json={"count": count}, headers=self.headers)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["batch_ids"], ids)
                    refresh.assert_called_once()
                request.assert_awaited_with(self.settings, "POST", "simulation/scenarios", {"count": count})
            for action, running, payload in (("start", True, {"speed": 1}), ("pause", False, None)):
                request.return_value = httpx.Response(200, json={"now": 123, "running": running, "speed": 1})
                response = self.client.post(f"/api/simulation/{action}", headers=self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["clock"]["running"], running)
                request.assert_awaited_with(self.settings, "POST", f"simulation/{action}", payload)

    @patch("app.simulation_operations.simulation_request", new_callable=AsyncMock)
    def test_status_uses_direct_dashboard_and_only_returns_clock(self, request):
        self.login()
        request.return_value = httpx.Response(200, json={"clock": {"now": 12, "running": False, "speed": 1}, "private": "ignored"})
        response = self.client.get("/api/simulation/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"clock", "fetched_at"})
        self.assertEqual(response.headers["cache-control"], "no-store")
        request.assert_awaited_with(self.settings, "GET", "dashboard")

    @patch("app.simulation_operations.simulation_request", new_callable=AsyncMock)
    def test_upstream_failures_are_sanitized_without_retry(self, request):
        self.login()
        for upstream, expected in ((401, 502), (403, 502), (404, 502), (409, 409), (422, 502), (500, 502)):
            request.reset_mock()
            request.return_value = httpx.Response(upstream, json={"detail": "gateway-secret secret-key"})
            with patch.object(self.app.state.data_center_reader, "request_refresh") as refresh:
                response = self.client.post("/api/simulation/scenarios", json={"count": 1}, headers=self.headers)
                self.assertEqual(response.status_code, expected)
                self.assertNotIn("secret", response.text)
                self.assertEqual(request.await_count, 1)
                refresh.assert_called_once()

    @patch("app.simulation_operations.simulation_request", new_callable=AsyncMock)
    def test_unconfirmed_success_is_not_reported_as_success(self, request):
        self.login()
        for result in ({"count": 2, "batch_ids": ["one", "two"]}, {"count": 1, "batch_ids": []}, {"count": 1, "batch_ids": [""]}, {"count": 1, "batch_ids": ["one", "one"]}, {"count": True, "batch_ids": ["one"]}, {}):
            request.return_value = httpx.Response(201, json=result)
            response = self.client.post("/api/simulation/scenarios", json={"count": 1}, headers=self.headers)
            self.assertEqual(response.status_code, 502)
            self.assertIn("不会自动重复提交", response.json()["detail"])
        request.return_value = httpx.Response(200, json={"now": 123, "running": False, "speed": 1})
        self.assertEqual(self.client.post("/api/simulation/start", headers=self.headers).status_code, 502)
        request.return_value = httpx.Response(200, content=b"invalid json")
        self.assertEqual(self.client.get("/api/simulation/status").status_code, 502)

    def test_transport_uses_credentials_and_proxy_and_never_retries_a_timeout(self):
        real_client = httpx.AsyncClient
        sent = []
        def respond(request):
            sent.append(request)
            raise httpx.ReadTimeout("secret-key gateway-secret", request=request)
        def client(**options):
            self.assertEqual(options["proxy"], self.settings.decoction_proxy_url)
            self.assertFalse(options["trust_env"])
            options.pop("proxy")
            return real_client(transport=httpx.MockTransport(respond), **options)
        with patch("app.simulation_operations.httpx.AsyncClient", side_effect=client):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(simulation_request(self.settings, "POST", "simulation/scenarios", {"count": 1}))
        self.assertEqual(len(sent), 1)
        self.assertEqual(str(sent[0].url), "https://simulation.example/api/v1/simulation/scenarios")
        self.assertEqual(json.loads(sent[0].content), {"count": 1})
        self.assertEqual(sent[0].headers["X-API-Key"], "secret-key")
        self.assertTrue(sent[0].headers["Authorization"].startswith("Basic "))
        self.assertIn("不会自动重复提交", caught.exception.detail)
        self.assertNotIn("secret", caught.exception.detail)

    def test_concurrent_command_is_rejected_without_second_write(self):
        self.login()
        async def exercise():
            entered, release = asyncio.Event(), asyncio.Event()
            async def slow_request(*args):
                entered.set()
                await release.wait()
                return httpx.Response(201, json={"count": 1, "batch_ids": ["one"]})
            with patch("app.simulation_operations.simulation_request", side_effect=slow_request) as request:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver", cookies=dict(self.client.cookies), headers=self.headers) as client:
                    first = asyncio.create_task(client.post("/api/simulation/scenarios", json={"count": 1}))
                    await asyncio.wait_for(entered.wait(), 2)
                    second = await client.post("/api/simulation/scenarios", json={"count": 1})
                    release.set()
                    result = await first
                self.assertEqual(second.status_code, 409)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(request.await_count, 1)
        asyncio.run(exercise())
