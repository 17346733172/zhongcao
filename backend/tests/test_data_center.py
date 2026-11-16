import secrets
import time
import unittest
import asyncio
from datetime import date, datetime, timedelta, timezone
from threading import Event
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.security import token_hash
from app.data_center_models import Snapshot


class DataCenterTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.settings = Settings(rag_enabled=False, database=Path(self.temp.name) / "test.db",
                                 decoction_base_url="https://simulation.example", decoction_api_key="test-secret",
                                 decoction_http_username="gateway-user", decoction_http_password="gateway-secret",
                                 decoction_proxy_url="http://127.0.0.1:9876")
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
        for path in ("snapshot", "prescriptions", "statistics"):
            self.assertEqual(self.client.get(f"/api/data-center/{path}").status_code, 401)
        get.assert_not_called()

    def test_statistics_auth_range_and_read_only_contract(self):
        self.login("viewer")
        reader = self.app.state.statistics_reader
        with patch.object(reader, "read", new=AsyncMock(return_value={"data": None, "synced_at": None, "stale": True, "error": "暂无数据"})) as read:
            for days in (1, 7, 30):
                response = self.client.get(f"/api/data-center/statistics?days={days}&refresh=true")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["cache-control"], "no-store")
                read.assert_awaited_with(days, True)
            for days in (0, 2, 31, "bad"):
                self.assertEqual(self.client.get(f"/api/data-center/statistics?days={days}").status_code, 422)
            self.assertEqual(read.await_count, 3)
        self.assertEqual(self.client.post("/api/data-center/statistics", headers={"X-CSRF-Protection": "1"}).status_code, 405)

    def test_custom_statistics_dates_are_forwarded_for_all_roles(self):
        reader = self.app.state.statistics_reader
        with patch.object(reader, "read", new=AsyncMock(return_value={"data": None, "synced_at": None, "stale": True, "error": None})) as read:
            for role in ("admin", "editor", "viewer"):
                self.login(role)
                response = self.client.get("/api/data-center/statistics?start_date=2026-11-06&end_date=2026-11-10")
                self.assertEqual(response.status_code, 200)
                read.assert_awaited_with(None, False, start_date=date(2026, 11, 6), end_date=date(2026, 11, 10))
            self.client.get("/api/data-center/statistics")
            read.assert_awaited_with(7, False)

    def test_invalid_custom_dates_never_reach_platform(self):
        self.login("viewer")
        tomorrow = (datetime.now(timezone(timedelta(hours=8))).date() + timedelta(days=1)).isoformat()
        invalid = ["start_date=2026-11-06", "end_date=2026-11-10",
                   "start_date=2026-11-10&end_date=2026-11-06",
                   "start_date=2026-11-06&end_date=" + tomorrow,
                   "start_date=2025-01-01&end_date=2026-11-10",
                   "start_date=invalid&end_date=2026-11-10",
                   "start_date=2026-02-30&end_date=2026-11-10",
                   "days=7&start_date=2026-11-06&end_date=2026-11-10"]
        with patch.object(self.app.state.statistics_reader, "_sync") as sync:
            for query in invalid:
                with self.subTest(query=query):
                    self.assertEqual(self.client.get("/api/data-center/statistics?" + query).status_code, 422)
            sync.assert_not_called()

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
        self.assertEqual(kwargs["proxy"], "http://127.0.0.1:9876")
        self.assertNotIn("secret", result.text)

    @patch("app.data_center.httpx.get")
    def test_snapshot_maps_running_fault_and_alarm_without_controls(self, get):
        self.login("viewer")
        payload = {"clock": {"now": 3600, "running": True, "speed": 1},
                   "summary": {"total_prescriptions": 1, "batch_counts": {"queued": 0, "running": 1, "paused": 0, "completed": 0, "cancelled": 0}, "dispatched_bags": 0, "active_alarms": 1, "waiting_batches": 0, "bags_per_virtual_hour": 0},
                   "devices": [{"id": "pot-01", "name": "锅 01", "kind": "pot", "kind_name": "煎药锅", "status": "fault", "batch_id": "batch-1", "capacity_ml": 30000, "utilization_percent": 12.5}],
                   "batches": [{"id": "batch-1", "prescription_id": "rx-1", "status": "running", "current_stage_name": "一煎", "progress_percent": 50, "temperature_c": 96, "trace_code": "trace-1", "steps": []}],
                   "alarms": [{"id": "alarm-1", "device_id": "pot-01", "batch_id": "batch-1", "message": "测试异常", "status": "active", "acknowledged": False, "created_at": 3000}]}
        self.app.state.data_center_reader.data = Snapshot.model_validate(payload)
        self.app.state.data_center_reader.fetched_at = datetime.now(timezone.utc)
        self.app.state.data_center_reader.start = AsyncMock()
        result = self.client.get("/api/data-center/snapshot")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["data"]["devices"][0]["status"], "fault")
        self.assertEqual(result.json()["data"]["alarms"][0]["message"], "测试异常")
        self.assertNotIn("steps", result.json()["data"]["batches"][0])
        get.assert_not_called()
        self.assertEqual(self.client.post("/api/data-center/snapshot", headers={"X-CSRF-Protection": "1"}).status_code, 405)

    @patch("app.data_center.httpx.get")
    def test_prescription_preserves_piece_quantity_recipe_and_review(self, get):
        self.login("viewer")
        prescription = {"id": "rx-1", "external_no": "TEST-1", "patient_code": "SIM-1", "status": "approved", "priority": 2, "doses": 5, "bags_per_dose": 2, "bag_volume_ml": 200,
                        "herbs": [{"name": "测试饮片", "unit": "piece", "quantity_per_dose": 3, "grams_per_dose": 4.5, "method": "late_add"},
                                  {"name": "测试枚饮片", "unit": "item", "quantity_per_dose": 3, "grams_per_dose": 6, "method": "normal"}], "batch_id": "batch-1", "created_at": 100,
                        "created_real_time": "2026-11-11T01:00:00+00:00", "recipe": {"first_decoct_seconds": 900}, "review": {"approved": True, "operator": "测试审核员", "comment": "已称重"}, "note": "测试备注"}
        get.return_value = httpx.Response(200, json={"items": [prescription], "total": 1, "offset": 0, "limit": 20})
        result = self.client.get("/api/data-center/prescriptions").json()["items"][0]
        self.assertEqual(result, prescription)

    @patch("app.data_center.httpx.get")
    def test_errors_are_readable_and_do_not_leak_upstream_credentials(self, get):
        self.login("viewer")
        for code, payload in ((401, {"detail": "gateway-secret"}), (403, {}), (404, {}), (500, {}), (200, {"unexpected": "test-secret"})):
            get.reset_mock()
            get.return_value = httpx.Response(code, json=payload)
            response = self.client.get("/api/data-center/prescriptions")
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("secret", response.text)
            self.assertEqual(get.call_count, 1)
        get.side_effect = httpx.ConnectTimeout("https://gateway-user:gateway-secret@simulation.example")
        response = self.client.get("/api/data-center/prescriptions")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("gateway", response.text)

    @patch("app.data_center.httpx.get")
    def test_transient_transport_failure_retries_same_read(self, get):
        self.login("viewer")
        for error in (httpx.ConnectTimeout("private detail"), httpx.ReadTimeout("private detail")):
            with self.subTest(error=type(error).__name__):
                get.reset_mock()
                get.side_effect = [error, httpx.Response(200, json={"items": [], "total": 25, "offset": 20, "limit": 20})]
                result = self.client.get("/api/data-center/prescriptions?offset=20&limit=20&status=approved")
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["total"], 25)
                self.assertEqual(get.call_count, 2)
                self.assertEqual(get.call_args_list[0], get.call_args_list[1])
                timeout = get.call_args.kwargs["timeout"]
                self.assertEqual((timeout.connect, timeout.read), (10, 20))

    @patch("app.data_center.httpx.get")
    def test_persistent_transport_failure_is_bounded_and_logs_only_type(self, get):
        self.login("viewer")
        for error, detail in ((httpx.ReadTimeout("gateway-secret"), "读取仿真平台超时"),
                              (httpx.ConnectError("gateway-secret"), "暂时无法连接仿真平台")):
            with self.subTest(error=type(error).__name__):
                get.reset_mock()
                get.side_effect = error
                with self.assertLogs("uvicorn.error", level="WARNING") as logs:
                    response = self.client.get("/api/data-center/prescriptions")
                self.assertEqual(response.status_code, 502)
                self.assertIn(detail, response.json()["detail"])
                self.assertEqual(get.call_count, 2)
                self.assertEqual(len(logs.output), 2)
                self.assertIn(type(error).__name__, logs.output[0])
                self.assertNotIn("gateway-secret", response.text + " ".join(logs.output))

    @patch("app.simulation_snapshot.httpx.AsyncClient.get")
    def test_snapshot_does_not_wait_for_platform_and_coalesces_readers(self, get):
        self.login("viewer")
        entered = Event()

        async def blocked(*args, **kwargs):
            entered.set()
            await asyncio.sleep(60)

        get.side_effect = blocked
        before = time.monotonic()
        result = self.client.get("/api/data-center/snapshot")
        self.assertEqual(result.status_code, 200)
        self.assertLess(time.monotonic() - before, 1)
        self.assertIsNone(result.json()["data"])
        self.assertIsNone(result.json()["fetched_at"])
        self.assertTrue(result.json()["refreshing"])
        self.assertTrue(entered.wait(1))
        for _ in range(5):
            self.assertEqual(self.client.get("/api/data-center/snapshot?refresh=true").status_code, 200)
        self.assertEqual(get.call_count, 1)

    @patch("app.data_center.httpx.get")
    def test_completed_batch_is_read_only_and_loaded_on_demand(self, get):
        self.assertEqual(self.client.get("/api/data-center/batches/batch_done").status_code, 401)
        get.assert_not_called()
        self.login("viewer")
        get.return_value = httpx.Response(200, json={"id": "batch_done", "prescription_id": "rx-1", "status": "completed", "progress_percent": 100, "temperature_c": 30, "trace_code": "trace_done", "steps": []})
        response = self.client.get("/api/data-center/batches/batch_done")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["trace_code"], "trace_done")
        self.assertNotIn("steps", response.json())
        self.assertTrue(get.call_args.args[0].endswith("/api/v1/batches/batch_done"))
        get.reset_mock()
        self.assertEqual(self.client.get("/api/data-center/batches/bad%3Fquery").status_code, 422)
        get.assert_not_called()

    @patch("app.data_center.httpx.get")
    def test_invalid_page_and_status_do_not_reach_platform(self, get):
        self.login("viewer")
        for query in ("limit=201", "offset=-1", "status=anything"):
            self.assertEqual(self.client.get("/api/data-center/prescriptions?" + query).status_code, 422)
        get.assert_not_called()
