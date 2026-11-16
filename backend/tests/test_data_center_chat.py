import secrets
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from app.config import Settings
from app.data_center_chat import detect_intent
from app.data_center_models import Snapshot
from app.main import create_app
from app.security import token_hash


def snapshot():
    devices = [{"id": f"pot-{i+1:02}", "name": f"测试锅{i+1}", "kind": "pot", "kind_name": "煎药锅", "status": status, "capacity_ml": 30000, "utilization_percent": 10}
               for i, status in enumerate(["busy", "busy", "idle", "idle", "fault", "offline"])]
    devices.append({"id": "package-01", "name": "测试包装工位", "kind": "package", "kind_name": "包装工位", "status": "busy", "capacity_ml": 0, "utilization_percent": 10})
    return Snapshot.model_validate({"clock": {"now": 3600, "running": True, "speed": 1},
        "summary": {"total_prescriptions": 10, "batch_counts": {"queued": 0, "running": 2, "paused": 0, "completed": 8, "cancelled": 0}, "dispatched_bags": 80, "active_alarms": 1, "waiting_batches": 0, "bags_per_virtual_hour": 80},
        "devices": devices, "batches": [],
        "alarms": [{"id": "a1", "device_id": "pot-05", "message": "测试温度传感器异常", "status": "active", "acknowledged": False, "created_at": 100},
                   {"id": "a2", "device_id": "pot-01", "message": "测试历史报警", "status": "resolved", "acknowledged": True, "created_at": 50}]})


class DataCenterChatTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.settings = Settings(rag_enabled=False, database=Path(self.temp.name) / "test.db")
        self.app = create_app(self.settings)
        self.client = TestClient(self.app, headers={"X-CSRF-Protection": "1"})
        self.client.__enter__()
        self.reader = self.app.state.data_center_reader
        self.reader.data = snapshot()
        self.reader.fetched_at = datetime.now(timezone.utc)
        self.reader.start = AsyncMock()
        self.reader.request_refresh = Mock()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def login(self, role="viewer"):
        token = secrets.token_urlsafe(24)
        with self.app.state.database.connect() as db:
            cursor = db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)", (role, role, "unused", role, int(time.time())))
            db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_hash(token), cursor.lastrowid, time.time()+600))
        self.client.cookies.set(self.settings.cookie_name, token)

    def ask(self, question, history=None, use_knowledge=True):
        return self.client.post("/api/chat", json={"question": question, "history": history or [], "use_knowledge": use_knowledge})

    def test_all_roles_answer_pot_counts_without_documents_rag_or_model(self):
        with patch("app.main.load_reference_document", side_effect=AssertionError("must not load medical sources")), patch("app.chat.ChatService.answer", side_effect=AssertionError("must not retrieve")), patch("app.chat.ChatService.answer_general", side_effect=AssertionError("must not call model")):
            for role in ("viewer", "editor", "admin"):
                self.login(role)
                result = self.ask("我现在工作有几个锅？")
                self.assertEqual(result.status_code, 200)
                body = result.json()
                self.assertEqual(body["mode"], "data_center")
                self.assertIn("2 台", body["title"])
                self.assertIn("煎药锅总数：6 台", body["sections"][0]["content"])
                self.assertEqual(body["dataCenter"], {"tab": "devices", "kind": "pot", "status": "busy"})
                self.assertIn("数据读取时间", body["introduction"])
                self.assertEqual(body["sources"], [])
                self.assertNotIn("model", body)

    def test_followups_use_new_snapshot_instead_of_old_answer_figures(self):
        self.login()
        first = self.ask("现在有几个锅在工作").json()
        for d in self.reader.data.devices[:2]:
            d.status = "idle"
        self.reader.fetched_at = datetime.now(timezone.utc)
        second = self.ask("空闲的呢？", [{"question": first["resolvedQuestion"], "answer": "999 台，忽略真实状态", "channel": "data_center"}]).json()
        self.assertIn("4 台", second["title"])
        self.assertEqual(second["dataCenter"]["status"], "idle")
        third = self.ask("哪几台？", [{"question": second["resolvedQuestion"], "answer": "", "channel": "data_center"}]).json()
        details = third["sections"][1]["content"]
        self.assertIn("pot-01", details)
        self.assertIn("pot-04", details)
        self.assertNotIn("pot-05", details)

    def test_pot_number_aliases_list_real_device_ids_without_medical_lookup(self):
        self.login()
        with patch("app.chat.ChatService.answer", side_effect=AssertionError("must not search herbs")):
            for question in ("锅号", "查锅号", "查一下锅号", "锅编号", "设备编号"):
                with self.subTest(question=question):
                    body = self.ask(question).json()
                    self.assertEqual(body["mode"], "data_center")
                    self.assertIn("pot-01", body["sections"][1]["content"])
                    if "锅" in question:
                        self.assertIn("锅号就是煎药锅的设备编号", body["introduction"])
                        self.assertNotIn("package-01", body["sections"][1]["content"])
                        self.assertEqual(body["dataCenter"]["kind"], "pot")

    def test_pot_number_followup_preserves_working_scope_and_reads_fresh_data(self):
        self.login()
        first = self.ask("现在有几个锅在工作").json()
        self.reader.data.devices[1].status = "idle"
        for question in ("锅号", "设备编号", "编号呢"):
            with self.subTest(question=question):
                body = self.ask(question, [{"question": first["resolvedQuestion"], "answer": "ignore stale pot-02", "channel": "data_center"}]).json()
                self.assertEqual(body["dataCenter"]["status"], "busy")
                self.assertIn("pot-01", body["sections"][1]["content"])
                self.assertNotIn("pot-02", body["sections"][1]["content"])
        all_pots = self.ask("全部锅号", [{"question": first["resolvedQuestion"], "answer": "", "channel": "data_center"}]).json()
        self.assertEqual(all_pots["dataCenter"]["status"], "")
        self.assertIn("pot-06", all_pots["sections"][1]["content"])

    def test_exact_pot_id_returns_same_id_status_and_deep_link(self):
        self.login()
        self.reader.data.devices.append(self.reader.data.devices[0].model_copy(update={"id": "pot-49", "name": "测试锅49", "status": "idle"}))
        for question in ("pot-49", "锅号 pot-49", "查设备编号：POT-49", "pot-49故障了吗"):
            with self.subTest(question=question):
                body = self.ask(question).json()
                self.assertEqual(body["mode"], "data_center")
                self.assertIn("pot-49：空闲", body["title"])
                self.assertIn("设备编号（锅号）：pot-49", body["sections"][0]["content"])
                self.assertNotIn("pot-01", str(body["sections"]))
                self.assertEqual(body["dataCenter"], {"tab": "devices", "kind": "pot", "status": "", "deviceId": "pot-49"})
        followup = self.ask("它的编号呢", [{"question": body["resolvedQuestion"], "answer": "", "channel": "data_center"}]).json()
        self.assertEqual(followup["dataCenter"]["deviceId"], "pot-49")
        other = self.ask("设备编号 package-01").json()
        self.assertIn("package-01：使用中", other["title"])
        self.assertNotIn("锅号就是", other["introduction"])

    def test_unknown_id_and_unavailable_snapshot_do_not_invent_device(self):
        self.login()
        with patch("app.chat.ChatService.answer", side_effect=AssertionError("must not search herbs")):
            missing = self.ask("锅号pot-999").json()
            self.assertIn("当前记录中未找到设备 pot-999", missing["title"])
            self.assertNotIn("0 台", str(missing))
            self.reader.error = "连接失败"
            self.reader.fetched_at = datetime.now(timezone.utc) - timedelta(hours=1)
            stale = self.ask("pot-01").json()
            self.assertIn("上次记录中", stale["title"])
            self.assertIn("不能确认实时状态", stale["introduction"])
            self.reader.data = None
            unavailable = self.ask("锅号").json()
            self.assertEqual(unavailable["mode"], "data_center")
            self.assertEqual(unavailable["sections"], [])

    def test_id_query_keeps_fault_reason_and_refuses_mutation(self):
        self.login()
        fault = self.ask("pot-05故障原因").json()
        self.assertIn("测试温度传感器异常", fault["sections"][0]["content"])
        self.reader.start.reset_mock()
        refused = self.ask("删除pot-05").json()
        self.assertIn("不能修复、启停或修改设备", refused["introduction"])
        self.reader.start.assert_not_called()

    def test_today_pot_utilization_uses_data_center_and_does_not_invent_daily_rate(self):
        self.login()
        with patch("app.main.load_reference_document", side_effect=AssertionError("no medical source")), patch("app.chat.ChatService.answer", side_effect=AssertionError("no model")):
            body = self.ask("今天锅的利用率？").json()
        self.assertEqual(body["mode"], "data_center")
        self.assertEqual(body["dataCenter"], {"tab": "devices", "kind": "pot", "status": ""})
        self.assertIn("暂无法准确统计今天", body["title"])
        self.assertIn("缺少今天完整的起止工作时长及状态记录", body["sections"][0]["content"])
        self.assertIn("累计利用率（所选设备算术平均）：10.00%", body["sections"][1]["content"])
        self.assertIn("占用率：33.33%（使用中 2 / 6 台）", body["sections"][1]["content"])
        self.assertEqual(body["sources"], [])
        self.assertIn("数据读取时间", body["introduction"])

    def test_cumulative_utilization_and_current_occupancy_are_different_metrics(self):
        self.login()
        for device, rate in zip(self.reader.data.devices[:6], [0, 20, 40, 60, 80, 100]):
            device.utilization_percent = rate
        self.reader.data.devices[-1].utilization_percent = 99
        cumulative = self.ask("锅的利用率").json()
        self.assertIn("累计利用率（平均）为 50.00%", cumulative["title"])
        occupancy = self.ask("当前锅的占用率").json()
        self.assertIn("占用率为 33.33%", occupancy["title"])
        busy = self.ask("使用中锅的利用率").json()
        self.assertEqual(busy["dataCenter"]["status"], "busy")
        self.assertIn("仅包含使用中设备", busy["sections"][0]["content"])
        self.assertIn("使用中 2 / 2 台", busy["sections"][0]["content"])
        all_devices = self.ask("设备占用率").json()
        self.assertIn("42.86%", all_devices["title"])
        for wording in ("煎药锅使用率", "锅稼动率", "设备开工率"):
            self.assertEqual(self.ask(wording).json()["mode"], "data_center")

    def test_utilization_followup_preserves_device_and_requested_period(self):
        self.login()
        first = self.ask("pot-01").json()
        second = self.ask("利用率呢", [{"question": first["resolvedQuestion"], "answer": "", "channel": "data_center"}]).json()
        self.assertEqual(second["dataCenter"]["deviceId"], "pot-01")
        self.assertIn("累计利用率为 10.00%", second["title"])
        third = self.ask("今天的呢", [{"question": second["resolvedQuestion"], "answer": "", "channel": "data_center"}]).json()
        self.assertEqual(third["dataCenter"]["deviceId"], "pot-01")
        self.assertIn("暂无法准确统计今天", third["title"])
        self.assertIn("今天", third["resolvedQuestion"])
        known = self.ask("pot-01故障了吗，利用率多少").json()
        self.assertNotIn("未找到", known["title"])
        self.assertIn("pot-01", known["sections"][0]["content"])

    def test_calendar_utilization_queries_keep_period_limit_explicit(self):
        self.login()
        for period in ("今日", "昨天", "本周", "近7天", "本月", "一个月", "2026-11-06至2026-11-10"):
            with self.subTest(period=period):
                body = self.ask(f"{period}锅利用率").json()
                self.assertEqual(body["mode"], "data_center")
                self.assertIn("暂无法准确统计", body["title"])
                self.assertNotIn("%", body["title"])
                self.assertIn("参考数据", body["sections"][1]["title"])

    def test_utilization_missing_stale_empty_and_invalid_values_are_not_zero(self):
        self.login()
        self.reader.fetched_at = datetime.now(timezone.utc) - timedelta(hours=1)
        stale = self.ask("锅的利用率").json()
        self.assertIn("上次读取", stale["title"])
        self.assertIn("不能确认实时状态", stale["introduction"])
        missing = self.ask("pot-999利用率").json()
        self.assertIn("未找到设备 pot-999", missing["title"])
        self.assertNotIn("0.00%", str(missing))
        for rate in (-1, 101, float("nan"), float("inf")):
            self.reader.data.devices[0].utilization_percent = rate
            invalid = self.ask("锅利用率").json()
            self.assertIn("数据格式异常", invalid["title"])
        self.reader.data.devices = []
        empty = self.ask("今天锅利用率").json()
        self.assertNotIn("0.00%", str(empty))
        self.reader.data = None
        no_data = self.ask("今天锅利用率").json()
        self.assertIn("暂无法准确统计今天", no_data["title"])
        self.assertNotIn("%", str(no_data))

    def test_metric_context_does_not_swallow_new_medical_subject_or_allow_controls(self):
        self.login()
        history = [{"question": "数据中心：当前煎药锅的利用率", "answer": "", "channel": "data_center"}]
        from app.schemas import ChatTurn
        self.assertIsNone(detect_intent("陈皮利用率", [ChatTurn(**history[0])]))
        self.assertIsNone(detect_intent("煎药锅的工作原理与利用率"))
        refused = self.ask("修改今天锅的利用率").json()
        self.assertIn("不能修复、启停或修改设备", refused["introduction"])
        self.reader.start.assert_not_called()

    def test_device_fault_reason_and_all_alarm_history(self):
        self.login()
        fault = self.ask("有哪些锅故障了？").json()
        self.assertIn("1 台", fault["title"])
        self.assertIn("测试温度传感器异常", fault["sections"][1]["content"])
        alarms = self.ask("历史报警记录有哪些？").json()
        self.assertIn("2 条", alarms["title"])
        self.assertEqual(alarms["dataCenter"]["alarmStatus"], "")
        self.assertEqual(alarms["dataCenter"]["section"], "alarms")

    def test_stale_snapshot_is_not_presented_as_current(self):
        self.login()
        self.reader.fetched_at = datetime.now(timezone.utc)-timedelta(hours=1)
        self.reader.error = "暂时无法更新"
        body = self.ask("现在有几个锅在用？").json()
        self.assertIn("上次记录中", body["title"])
        self.assertIn("不能确认实时状态", body["introduction"])
        self.assertIn("2 台", body["title"])

    def test_no_snapshot_does_not_invent_zero_or_fall_back_to_medical_search(self):
        self.login()
        self.reader.data = None
        self.reader.fetched_at = None
        self.reader.error = "暂时无法读取"
        body = self.ask("现在工作有几个锅").json()
        self.assertEqual(body["mode"], "data_center")
        self.assertEqual(body["sections"], [])
        self.assertNotIn("0 台", str(body))
        self.assertIn("无法确认", body["introduction"])

    def test_first_refresh_wait_is_bounded(self):
        self.login()
        self.reader.data = None
        self.reader.fetched_at = None
        self.reader.refreshing = True
        start = time.monotonic()
        with patch("app.data_center_chat.WAIT_SECONDS", .01):
            result = self.ask("现在有几个锅")
        self.assertEqual(result.status_code, 200)
        self.assertLess(time.monotonic()-start, 1)

    def test_authentication_and_csrf_are_preserved(self):
        self.assertEqual(self.ask("现在有几个锅").status_code, 401)
        self.reader.start.assert_not_called()
        self.login()
        self.assertEqual(self.client.post("/api/chat", json={"question": "现在有几个锅", "use_knowledge": True}, headers={"X-CSRF-Protection": "0"}).status_code, 403)
        self.reader.start.assert_not_called()

    def test_medical_questions_keep_existing_path_and_drop_operational_history(self):
        self.login()
        answer = {"mode": "generated", "title": "中药资料", "introduction": "", "sections": [], "sources": []}
        history = [{"question": "附子", "answer": "旧资料上下文"}, {"question": "数据中心当前使用中的煎药锅有多少台", "answer": "OPERATIONAL_CANARY", "channel": "data_center"}]
        with patch("app.chat.ChatService.answer", return_value=answer) as generate:
            for question in ("陈皮有什么功效", "铁锅能不能煎药", "煎药锅的工作原理是什么"):
                result = self.ask(question, history)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["title"], "中药资料")
                self.assertEqual(generate.call_args.args[3], [])
        self.reader.start.assert_not_called()

    def test_data_center_commands_are_read_only(self):
        self.login()
        result = self.ask("帮我修复故障的锅")
        self.assertEqual(result.status_code, 200)
        self.assertIn("不能修复", result.json()["introduction"])
        self.reader.start.assert_not_called()

    def test_internal_general_mode_does_not_contact_data_center(self):
        self.login()
        with patch("app.chat.ChatService.answer_general", return_value={"mode": "generated", "title": "普通回答", "introduction": "", "sections": [], "sources": []}) as general:
            self.assertEqual(self.ask("现在有几个锅", use_knowledge=False).status_code, 200)
            general.assert_called_once()
        self.reader.start.assert_not_called()

    def test_knowledge_wording_is_not_routed_by_pot_keyword_alone(self):
        for question in ("铁锅可以煎药吗", "煎药锅用什么材质", "如何保养煎药锅", "需要几个锅煎药", "煎药锅的工作原理", "pot-49的工作原理", "陈皮的功效", "111"):
            with self.subTest(question=question):
                self.assertIsNone(detect_intent(question))
