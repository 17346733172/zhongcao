import secrets
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.config import Settings
from app.main import create_app
from app.security import token_hash
from app.data_center_models import Snapshot

KINDS = ["dispenser", "verification", "conveyor", "water", "soaking", "decocter", "filter", "packer", "labeler", "quality", "dispatch", "residue", "washer"]


def page(revision=0, seconds=600):
    return {"items": [{"kind": kind, "name": kind, "default_processing_seconds": seconds} for kind in KINDS], "revision": revision}


class DeviceDefaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(rag_enabled=False, database=Path(self.temp.name) / "test.db")
        self.app = create_app(self.settings)
        self.client = self.enterContext(TestClient(self.app))
        self.headers = {"X-CSRF-Protection": "1"}

    def login(self, role="viewer"):
        token = secrets.token_urlsafe(24)
        with self.app.state.database.connect() as db:
            result = db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)", (role, role, "unused", role, time.time()))
            db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_hash(token), result.lastrowid, time.time() + 600))
        self.client.cookies.set(self.settings.cookie_name, token)

    def snapshot(self, age=0):
        reader = self.app.state.data_center_reader
        reader.data = Snapshot.model_validate({"clock": {"now": 0, "running": False, "speed": 1},
            "summary": {"total_prescriptions": 0, "batch_counts": dict.fromkeys(("queued", "running", "paused", "completed", "cancelled"), 0), "dispatched_bags": 0, "active_alarms": 0, "waiting_batches": 0, "bags_per_virtual_hour": 0},
            "devices": [{"id": "dispenser-01", "name": "调剂机", "kind_name": "调剂机", "kind": "dispenser", "status": "idle", "capacity_ml": 0, "utilization_percent": 0, "default_processing_seconds": 600}], "batches": [], "alarms": []})
        reader.fetched_at = datetime.now(timezone.utc) - timedelta(seconds=age)
        return reader

    @patch("app.device_defaults.simulation_request", new_callable=AsyncMock)
    def test_auth_csrf_and_invalid_values_prevent_platform_writes(self, request):
        endpoint = "/api/simulation/device-defaults/dispenser"
        self.assertEqual(self.client.get("/api/simulation/device-defaults").status_code, 401)
        self.assertEqual(self.client.post(endpoint, json={}, headers=self.headers).status_code, 401)
        self.login()
        self.assertEqual(self.client.post(endpoint, json={}).status_code, 403)
        self.assertEqual(self.client.post(endpoint, json={}, headers={**self.headers, "Origin": "https://bad.example"}).status_code, 403)
        for seconds in (0, 5, 7201, True, "300"):
            response = self.client.post(endpoint, json={"default_processing_seconds": seconds, "expected_revision": 0}, headers=self.headers)
            self.assertEqual(response.status_code, 422)
            self.assertIn("0.1–120", response.json()["detail"])
        self.assertEqual(self.client.post(endpoint.replace("dispenser", "pot"), json={"default_processing_seconds": 300, "expected_revision": 0}, headers=self.headers).status_code, 422)
        request.assert_not_called()

    @patch("app.device_defaults.simulation_request", new_callable=AsyncMock)
    def test_all_roles_read_and_save_verified_revision_with_one_write(self, request):
        for role in ("viewer", "editor", "admin"):
            self.login(role)
            request.return_value = httpx.Response(200, json=page())
            self.assertTrue(self.client.get("/api/simulation/device-defaults").json()["supported"])
            request.reset_mock()
            request.return_value = httpx.Response(200, json=page(revision=1, seconds=450))
            with patch.object(self.app.state.data_center_reader, "request_refresh") as refresh:
                result = self.client.post("/api/simulation/device-defaults/dispenser", json={"default_processing_seconds": 450, "expected_revision": 0}, headers=self.headers)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["revision"], 1)
                self.assertEqual(result.headers["cache-control"], "no-store")
                refresh.assert_called_once()
            request.assert_awaited_once_with(self.settings, "POST", "device-defaults/dispenser", {"default_processing_seconds": 450.0, "expected_revision": 0})

    @patch("app.device_defaults.simulation_request", new_callable=AsyncMock)
    def test_old_platform_is_read_only_and_current_values_come_from_dashboard(self, request):
        self.login()
        dashboard = {"clock": {"now": 0, "running": False, "speed": 1}, "total_prescriptions": 0, "batch_counts": dict.fromkeys(("queued", "running", "paused", "completed", "cancelled"), 0), "dispatched_bags": 0, "active_alarms": 0, "waiting_batches": 0, "bags_per_virtual_hour": 0,
                     "devices": [{"id": "dispenser-01", "name": "调剂机", "kind_name": "调剂机", "kind": "dispenser", "status": "idle", "capacity_ml": 0, "utilization_percent": 0, "default_processing_seconds": 600}]}
        request.side_effect = [httpx.Response(404), httpx.Response(200, json=dashboard)]
        result = self.client.get("/api/simulation/device-defaults").json()
        self.assertFalse(result["supported"])
        self.assertIsNone(result["revision"])
        self.assertEqual(result["items"][0]["default_processing_seconds"], 600)
        self.assertIn("更新平台", result["notice"])
        self.assertEqual(request.await_count, 2)

    @patch("app.device_defaults.simulation_request", new_callable=AsyncMock)
    def test_bad_receipt_conflict_and_failure_never_claim_save_or_retry(self, request):
        self.login()
        for code, payload in ((409, {}), (404, {}), (500, {"detail": "secret"}), (200, page()), (200, page(1, 300)), (200, {"items": [], "revision": 1})):
            request.reset_mock()
            request.return_value = httpx.Response(code, json=payload)
            result = self.client.post("/api/simulation/device-defaults/dispenser", json={"default_processing_seconds": 450, "expected_revision": 0}, headers=self.headers)
            self.assertIn(result.status_code, (409, 502))
            self.assertNotIn("secret", result.text)
            self.assertEqual(request.await_count, 1)

    @patch("app.device_defaults.simulation_request", new_callable=AsyncMock)
    def test_legacy_uses_fresh_shared_snapshot_without_second_network_read(self, request):
        self.login()
        reader = self.snapshot()
        request.return_value = httpx.Response(404)
        result = self.client.get("/api/simulation/device-defaults").json()
        self.assertFalse(result["stale"])
        self.assertIsNone(result["error"])
        self.assertEqual(datetime.fromisoformat(result["fetched_at"]), reader.fetched_at)
        self.assertEqual(result["items"][0]["default_processing_seconds"], 600)
        request.assert_awaited_once_with(self.settings, "GET", "device-defaults")

    @patch("app.device_defaults.simulation_request", new_callable=AsyncMock)
    def test_legacy_stale_snapshot_retained_after_two_failed_dashboard_attempts(self, request):
        self.login()
        reader = self.snapshot(age=120)
        request.side_effect = [httpx.Response(404), HTTPException(502, "connection failed"), HTTPException(502, "connection failed")]
        response = self.client.get("/api/simulation/device-defaults")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["stale"])
        self.assertIn("上次", result["error"])
        self.assertEqual(datetime.fromisoformat(result["fetched_at"]), reader.fetched_at)
        self.assertEqual(request.await_count, 3)

    @patch("app.device_defaults.simulation_request", new_callable=AsyncMock)
    def test_capability_read_retries_transport_but_does_not_invent_legacy_support(self, request):
        self.login()
        self.snapshot()
        request.side_effect = [HTTPException(502, "暂时无法读取仿真平台状态，请重新读取。"), httpx.Response(200, json=page())]
        self.assertTrue(self.client.get("/api/simulation/device-defaults").json()["supported"])
        self.assertEqual(request.await_count, 2)
        request.reset_mock()
        request.side_effect = HTTPException(502, "暂时无法读取仿真平台状态，请重新读取。")
        response = self.client.get("/api/simulation/device-defaults")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["supported"])
        self.assertTrue(response.json()["capability_pending"])
        self.assertFalse(response.json()["stale"])
        self.assertEqual(response.json()["items"][0]["default_processing_seconds"], 600)
        self.assertNotIn("尚未提供", response.json()["notice"])
        self.assertEqual(request.await_count, 2)

    @patch("app.device_defaults.simulation_request", new_callable=AsyncMock)
    def test_manual_refresh_rechecks_cached_legacy_capability(self, request):
        self.login()
        self.snapshot()
        request.return_value = httpx.Response(404)
        self.client.get("/api/simulation/device-defaults")
        request.reset_mock()
        self.assertFalse(self.client.get("/api/simulation/device-defaults").json()["supported"])
        request.assert_not_called()
        request.return_value = httpx.Response(200, json=page())
        self.assertTrue(self.client.get("/api/simulation/device-defaults?refresh=true").json()["supported"])
        self.assertEqual(request.await_count, 1)

    @patch("app.device_defaults.simulation_request", new_callable=AsyncMock)
    def test_failed_legacy_read_without_cache_does_not_return_empty_success(self, request):
        self.login()
        request.side_effect = [httpx.Response(404), HTTPException(502, "connection failed"), HTTPException(502, "connection failed")]
        response = self.client.get("/api/simulation/device-defaults")
        self.assertEqual(response.status_code, 502)
        self.assertIn("设备默认用时", response.json()["detail"])
        self.assertNotIn("items", response.json())
