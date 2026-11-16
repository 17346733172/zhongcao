import asyncio
from contextlib import suppress
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

import httpx

from app.config import Settings
from app.simulation_snapshot import SnapshotReader


def dashboard():
    return {"clock": {"now": 3600, "running": True, "speed": 1},
            "total_prescriptions": 25,
            "batch_counts": {"queued": 2, "running": 1, "paused": 0, "completed": 22, "cancelled": 0},
            "dispatched_bags": 156, "active_alarms": 1, "waiting_batches": 2, "bags_per_virtual_hour": 2,
            "devices": [{"id": "pot-01", "name": "锅 01", "kind": "pot", "kind_name": "煎药锅", "status": "fault", "batch_id": "batch-1", "capacity_ml": 30000, "utilization_percent": 12.5}]}


def batch(identifier, status):
    return {"id": identifier, "prescription_id": "rx-1", "status": status, "current_stage_name": "一煎", "progress_percent": 50, "temperature_c": 96, "trace_code": "trace-1", "steps": [{"unused": True}]}


class SnapshotReaderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = TemporaryDirectory()
        self.settings = Settings(rag_enabled=False, database=Path(self.temp.name) / "test.db", decoction_base_url="https://simulation.example")
        self.reader = SnapshotReader(self.settings)
        self.requests = []
        self.clients = []
        self.handler = self.respond
        def new_client():
            client = httpx.AsyncClient(transport=httpx.MockTransport(self.handler), trust_env=False)
            self.clients.append(client)
            return client
        self.reader._new_client = new_client

    async def asyncTearDown(self):
        await self.reader.close()
        self.temp.cleanup()

    def respond(self, request):
        self.requests.append(request)
        path = request.url.path
        offset = int(request.url.params.get("offset", "0"))
        if path.endswith("/dashboard"):
            return httpx.Response(200, json=dashboard())
        if path.endswith("/alarms"):
            alarm = {"id": f"alarm-{offset}", "device_id": "pot-01", "message": "测试报警", "status": "active" if offset == 0 else "resolved", "acknowledged": False, "created_at": 100}
            return httpx.Response(200, json={"items": [alarm], "total": 2, "offset": offset, "limit": 1})
        if path.endswith("/batches"):
            status = request.url.params["status"]
            return httpx.Response(200, json={"items": [batch(f"{status}-{offset}", status)], "total": 2 if status == "queued" else 1, "offset": offset, "limit": 1})
        raise AssertionError("Full simulation history must not be downloaded")

    async def test_lightweight_refresh_paginates_active_batches_and_all_alarms(self):
        await self.reader.refresh()
        state = self.reader.state()
        self.assertIsNone(state.error)
        self.assertEqual(state.data.summary.total_prescriptions, 25)
        self.assertEqual(len(state.data.batches), 3)
        self.assertEqual(len(state.data.alarms), 2)
        self.assertEqual(state.data.devices[0].status, "fault")
        self.assertNotIn("steps", state.data.model_dump()["batches"][0])
        self.assertEqual(len(self.requests), 6)
        self.assertFalse(any(r.url.params.get("status") in {"completed", "paused"} for r in self.requests))
        self.assertTrue(self.reader.cache_file.exists())

    async def test_overview_preserves_platform_device_processing_time_and_old_cache(self):
        original = self.respond

        def with_duration(request):
            if request.url.path.endswith("/dashboard"):
                data = dashboard()
                data["devices"][0].update(kind="dispenser", kind_name="调剂机", default_processing_seconds=600)
                return httpx.Response(200, json=data)
            return original(request)

        self.handler = with_duration
        await self.reader.refresh()
        self.assertEqual(self.reader.state().data.devices[0].default_processing_seconds, 600)
        saved = json.loads(self.reader.cache_file.read_text(encoding="utf-8"))
        del saved["data"]["devices"][0]["default_processing_seconds"]
        self.reader.cache_file.write_text(json.dumps(saved), encoding="utf-8")
        restored = SnapshotReader(self.settings)
        self.assertIsNotNone(restored.data)
        self.assertIsNone(restored.data.devices[0].default_processing_seconds)

    async def test_cache_survives_restart_and_failure_without_changing_timestamp(self):
        await self.reader.refresh()
        original = self.reader.fetched_at
        restored = SnapshotReader(self.settings)
        self.assertEqual(restored.data, self.reader.data)
        self.assertEqual(restored.fetched_at, original)
        self.handler = self.fail_http
        await self.reader.refresh()
        self.assertEqual(self.reader.fetched_at, original)
        self.assertEqual(self.reader.data.summary.total_prescriptions, 25)
        self.assertTrue(self.reader.state().stale)
        self.assertIn("认证失败", self.reader.error)
        self.assertEqual(SnapshotReader(self.settings).fetched_at, original)
        other_source = SnapshotReader(replace(self.settings, decoction_base_url="https://other.example"))
        self.assertIsNone(other_source.data)
        saved = self.reader.cache_file.read_text(encoding="utf-8")
        self.assertNotIn("simulation.example", saved)
        self.assertNotIn("private-secret", saved + self.reader.error)

    async def fail_http(self, *args, **kwargs):
        return httpx.Response(401, json={"detail": "private-secret"})

    async def test_total_deadline_cancels_slow_request_and_keeps_existing_data(self):
        await self.reader.refresh()
        original = self.reader.fetched_at
        cancelled = False

        async def slow(*args, **kwargs):
            nonlocal cancelled
            try:
                await asyncio.sleep(60)
            finally:
                cancelled = True

        self.handler = slow
        start = time.monotonic()
        with patch("app.simulation_snapshot.REFRESH_TIMEOUT_SECONDS", 0.02):
            await self.reader.refresh()
        self.assertLess(time.monotonic() - start, 0.5)
        self.assertTrue(cancelled)
        self.assertEqual(self.reader.fetched_at, original)
        self.assertTrue(self.reader.state().stale)
        self.assertFalse(self.reader.refreshing)
        self.assertIsNone(self.reader._client)
        self.assertTrue(self.clients[-1].is_closed)
        self.handler = self.respond
        await self.reader.refresh()
        self.assertIsNone(self.reader.error)
        self.assertGreater(self.reader.fetched_at, original)

    async def test_invalid_cache_or_page_cannot_produce_fake_statistics(self):
        self.reader.cache_file.write_text('{"source":"invalid"}', encoding="utf-8")
        self.assertIsNone(SnapshotReader(self.settings).data)

        async def empty_page(url, **kwargs):
            if url.endswith("dashboard"):
                return httpx.Response(200, json=dashboard())
            return httpx.Response(200, json={"items": [], "offset": 0, "total": 2, "limit": 200})

        self.handler = lambda request: empty_page(str(request.url))
        await self.reader.refresh()
        self.assertIsNone(self.reader.data)
        self.assertIsNone(self.reader.fetched_at)
        self.assertIn("分页", self.reader.error)

    async def test_pool_timeout_retries_with_a_new_client_and_recovers(self):
        clients = []

        def failed_pool(request):
            raise httpx.PoolTimeout("private proxy detail")

        def new_client():
            handler = failed_pool if not clients else self.respond
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)
            clients.append(client)
            return client

        self.reader._new_client = new_client
        with self.assertLogs("uvicorn.error", level="WARNING") as logs:
            await self.reader.refresh()
        self.assertEqual(len(clients), 2)
        self.assertTrue(all(client.is_closed for client in clients))
        self.assertIsNone(self.reader._client)
        self.assertIsNone(self.reader.error)
        self.assertEqual(self.reader.data.summary.total_prescriptions, 25)
        self.assertIn("PoolTimeout", logs.output[0])
        self.assertNotIn("private proxy detail", " ".join(logs.output))

    async def test_repeated_real_proxy_handshake_failures_recover_without_restart(self):
        await self.reader.refresh()
        original = self.reader.fetched_at
        good_factory = self.reader._new_client
        failed_clients = []

        async def failed_tunnel(reader, writer):
            try:
                await reader.readuntil(b"\r\n\r\n")
                writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await writer.drain()
            except (ConnectionError, asyncio.IncompleteReadError):
                pass
            finally:
                writer.close()
                with suppress(ConnectionError):
                    await writer.wait_closed()

        server = await asyncio.start_server(failed_tunnel, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        self.reader.settings = replace(self.settings, decoction_proxy_url=f"http://127.0.0.1:{port}")

        def real_factory():
            client = SnapshotReader._new_client(self.reader)
            failed_clients.append(client)
            return client

        self.reader._new_client = real_factory
        async with server:
            with self.assertLogs("uvicorn.error", level="WARNING") as logs:
                for _ in range(6):
                    await self.reader.refresh()
                    self.assertEqual(self.reader.fetched_at, original)
                    self.assertTrue(self.reader.state().stale)
                    self.assertIsNone(self.reader._client)
        self.assertEqual(len(failed_clients), 12)
        self.assertTrue(all(client.is_closed for client in failed_clients))
        self.assertNotIn("PoolTimeout", " ".join(logs.output))
        # Restore the successful platform transport on this same running reader.
        self.reader._new_client = good_factory
        await self.reader.refresh()
        self.assertIsNone(self.reader.error)
        self.assertFalse(self.reader.state().stale)
        self.assertGreater(self.reader.fetched_at, original)

    async def test_background_auth_is_configured_and_never_returned(self):
        settings = replace(self.settings, decoction_api_key="private-api", decoction_http_username="private-user", decoction_http_password="private-secret", decoction_proxy_url="http://127.0.0.1:9876")
        reader = SnapshotReader(settings)
        with patch("app.simulation_snapshot.httpx.AsyncClient", wraps=httpx.AsyncClient) as constructor:
            await reader.start()
            self.assertEqual(constructor.call_args.kwargs["headers"], {"X-API-Key": "private-api"})
            self.assertIsInstance(constructor.call_args.kwargs["auth"], httpx.BasicAuth)
            self.assertFalse(constructor.call_args.kwargs["trust_env"])
            self.assertEqual(constructor.call_args.kwargs["proxy"], "http://127.0.0.1:9876")
            await reader.close()
        self.assertNotIn("private", reader.state().model_dump_json())
