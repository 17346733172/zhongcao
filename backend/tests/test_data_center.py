import secrets
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.security import token_hash


class DataCenterTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.settings = Settings(rag_enabled=False, database=Path(self.temp.name) / "test.db",
                                 decoction_base_url="https://simulation.example", decoction_api_key="test-secret",
                                 decoction_http_username="gateway-user", decoction_http_password="gateway-secret")
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def login(self, role):
        token = secrets.token_urlsafe(24)
        with self.app.state.database.connect() as db:
            cursor = db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                                (role, role, "unused", role, int(time.time())))
            db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_hash(token), cursor.lastrowid, time.time() + 600))
        self.client.cookies.set(self.settings.cookie_name, token)

    @patch("app.data_center.httpx.get")
    def test_anonymous_cannot_contact_platform(self, get):
        for path in ("snapshot", "prescriptions"):
            self.assertEqual(self.client.get(f"/api/data-center/{path}").status_code, 401)
        get.assert_not_called()

    @patch("app.data_center.httpx.get")
    def test_all_roles_can_read_and_pagination_is_forwarded(self, get):
        get.return_value = httpx.Response(200, json={"items": [], "total": 24, "offset": 20, "limit": 20})
        for role in ("admin", "editor", "viewer"):
            self.login(role)
            result = self.client.get("/api/data-center/prescriptions?status=approved&offset=20&limit=20")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["total"], 24)
            self.assertEqual(result.headers["cache-control"], "no-store")
        args, kwargs = get.call_args
        self.assertEqual(args[0], "https://simulation.example/api/v1/prescriptions")
        self.assertEqual(kwargs["params"], {"status": "approved", "offset": 20, "limit": 20})
        self.assertEqual(kwargs["headers"], {"X-API-Key": "test-secret"})
        self.assertIsInstance(kwargs["auth"], httpx.BasicAuth)
        self.assertFalse(kwargs["trust_env"])
        self.assertNotIn("secret", result.text)

    @patch("app.data_center.httpx.get")
    def test_snapshot_maps_running_fault_and_alarm_without_controls(self, get):
        self.login("viewer")
        payload = {"clock": {"now": 3600, "running": True, "speed": 1},
                   "summary": {"total_prescriptions": 1, "batch_counts": {"queued": 0, "running": 1, "paused": 0, "completed": 0, "cancelled": 0}, "dispatched_bags": 0, "active_alarms": 1, "waiting_batches": 0, "bags_per_virtual_hour": 0},
                   "devices": [{"id": "pot-01", "name": "锅 01", "kind": "pot", "kind_name": "煎药锅", "status": "fault", "batch_id": "batch-1", "capacity_ml": 30000, "utilization_percent": 12.5}],
                   "batches": [{"id": "batch-1", "prescription_id": "rx-1", "status": "running", "current_stage_name": "一煎", "progress_percent": 50, "temperature_c": 96, "trace_code": "trace-1", "steps": []}],
                   "alarms": [{"id": "alarm-1", "device_id": "pot-01", "batch_id": "batch-1", "message": "测试异常", "status": "active", "acknowledged": False, "created_at": 3000}]}
        get.return_value = httpx.Response(200, json=payload)
        result = self.client.get("/api/data-center/snapshot")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["devices"][0]["status"], "fault")
        self.assertEqual(result.json()["alarms"][0]["message"], "测试异常")
        self.assertNotIn("steps", result.json()["batches"][0])
        self.assertEqual(self.client.post("/api/data-center/snapshot", headers={"X-CSRF-Protection": "1"}).status_code, 405)

    @patch("app.data_center.httpx.get")
    def test_prescription_preserves_piece_quantity_recipe_and_review(self, get):
        self.login("viewer")
        prescription = {"id": "rx-1", "external_no": "TEST-1", "patient_code": "SIM-1", "status": "approved", "priority": 2, "doses": 5, "bags_per_dose": 2, "bag_volume_ml": 200,
                        "herbs": [{"name": "测试饮片", "unit": "piece", "quantity_per_dose": 3, "grams_per_dose": 4.5, "method": "late_add"}], "batch_id": "batch-1", "created_at": 100,
                        "created_real_time": "2026-11-11T01:00:00+00:00", "recipe": {"first_decoct_seconds": 900}, "review": {"approved": True, "operator": "测试审核员", "comment": "已称重"}, "note": "测试备注"}
        get.return_value = httpx.Response(200, json={"items": [prescription], "total": 1, "offset": 0, "limit": 20})
        result = self.client.get("/api/data-center/prescriptions").json()["items"][0]
        self.assertEqual(result, prescription)

    @patch("app.data_center.httpx.get")
    def test_errors_are_readable_and_do_not_leak_upstream_credentials(self, get):
        self.login("viewer")
        for code, payload in ((401, {"detail": "gateway-secret"}), (403, {}), (404, {}), (500, {}), (200, {"unexpected": "test-secret"})):
            get.return_value = httpx.Response(code, json=payload)
            response = self.client.get("/api/data-center/snapshot")
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("secret", response.text)
        get.side_effect = httpx.ConnectTimeout("https://gateway-user:gateway-secret@simulation.example")
        response = self.client.get("/api/data-center/prescriptions")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("gateway", response.text)

    @patch("app.data_center.httpx.get")
    def test_invalid_page_and_status_do_not_reach_platform(self, get):
        self.login("viewer")
        for query in ("limit=201", "offset=-1", "status=anything"):
            self.assertEqual(self.client.get("/api/data-center/prescriptions?" + query).status_code, 422)
        get.assert_not_called()
