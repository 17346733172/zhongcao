import asyncio
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx

from app.config import Settings
from app.database import Database
from app.simulation_statistics import StatisticsReader


UTC = timezone.utc
NOW = datetime(2026, 11, 13, 10, tzinfo=UTC)


def event(id, kind, at="2026-11-13T01:00:00+00:00", **payload):
    return {"id": id, "type": kind, "real_time": at, "sim_time": 999999,
            "entity_id": "private-patient-id", "payload": payload}


class StatisticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.settings = Settings(database=Path(self.temp.name) / "test.db", rag_enabled=False,
                                 decoction_base_url="https://simulation.example")
        self.db = Database(self.settings.database)
        self.db.initialize()
        self.reader = StatisticsReader(self.settings, self.db)

    async def asyncTearDown(self):
        await self.reader.close()
        self.temp.cleanup()

    def seed(self, earliest, rows=(), end=NOW):
        with self.db.connect() as db:
            db.execute("INSERT OR REPLACE INTO simulation_history_state VALUES(?,?,?,?)",
                       (self.reader.source, "test-origin", earliest.timestamp() if earliest else None, end.timestamp()))
            db.executemany("INSERT INTO simulation_events VALUES(?,?,?,?,?)", [
                (self.reader.source, i, kind, datetime.fromisoformat(at).timestamp(), amount)
                for i, kind, at, amount in rows
            ])

    def mock_platform(self, records, calls=None, fail_type=None):
        def handler(request):
            query = request.url.params
            if calls is not None:
                calls.append(dict(query))
            if query.get("event_type") == fail_type and fail_type:
                return httpx.Response(503, json={"detail": "private-upstream-detail"})
            after, limit = int(query["after_id"]), int(query["limit"])
            selected = [e for e in records if e["id"] > after and (
                not query.get("event_type") or e["type"] == query["event_type"])]
            selected.sort(key=lambda e: e["id"])
            selected = selected[:limit]
            return httpx.Response(200, json={"items": selected,
                                           "next_after_id": selected[-1]["id"] if selected else after})
        self.reader._new_client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def test_beijing_midnight_and_seven_thirty_day_boundaries(self):
        self.seed(datetime(2026, 10, 1, tzinfo=UTC), [
            (1, "prescription.created", "2026-11-12T15:59:59+00:00", 1),
            (2, "prescription.created", "2026-11-12T16:00:00+00:00", 1),
            (3, "batch.completed", "2026-11-06T16:00:00+00:00", 1),
            (4, "batch.completed", "2026-11-06T15:59:59+00:00", 1),
            (5, "product.dispatched", "2026-10-14T16:00:00+00:00", 10),
            (6, "product.dispatched", "2026-10-14T15:59:59+00:00", 20),
            (7, "prescription.created", "2026-11-13T10:00:01+00:00", 1),
        ])
        today = self.reader.report(1, NOW).data
        self.assertEqual(today.totals.prescriptions, 1)
        self.assertEqual(today.daily[0].date.isoformat(), "2026-11-13")
        week = self.reader.report(7, NOW).data
        self.assertEqual((len(week.daily), week.totals.completed), (7, 1))
        self.assertEqual(week.daily[0].date.isoformat(), "2026-11-07")
        month = self.reader.report(30, NOW).data
        self.assertEqual((len(month.daily), month.totals.dispatched_bags), (30, 10))
        self.assertEqual(month.daily[0].date.isoformat(), "2026-10-15")
        self.assertFalse(month.partial)

    async def test_missing_history_is_not_zero_and_first_day_is_partial(self):
        self.seed(datetime(2026, 11, 10, 3, tzinfo=UTC))
        report = self.reader.report(7, NOW).data
        self.assertTrue(report.partial)
        self.assertIsNone(report.daily[0].totals)
        self.assertEqual(report.daily[3].coverage, "partial")
        self.assertEqual(report.daily[-1].coverage, "complete")
        self.assertEqual(report.daily[-1].totals.prescriptions, 0)

    async def test_custom_dates_include_both_days_and_exclude_the_next_midnight(self):
        self.seed(datetime(2026, 11, 1, tzinfo=UTC), [
            (1, "prescription.created", "2026-11-08T15:59:59+00:00", 1),
            (2, "prescription.created", "2026-11-08T16:00:00+00:00", 1),
            (3, "prescription.created", "2026-11-10T15:59:59+00:00", 1),
            (4, "prescription.created", "2026-11-10T16:00:00+00:00", 1),
            (5, "product.dispatched", "2026-11-09T04:00:00+00:00", 12),
        ])
        report = self.reader.report(now=NOW, start_date=date(2026, 11, 9), end_date=date(2026, 11, 10)).data
        self.assertEqual(report.days, 2)
        self.assertEqual([str(day.date) for day in report.daily], ["2026-11-09", "2026-11-10"])
        self.assertEqual((report.totals.prescriptions, report.totals.dispatched_bags), (2, 12))
        same_day = self.reader.report(now=NOW, start_date=date(2026, 11, 10), end_date=date(2026, 11, 10)).data
        self.assertEqual((same_day.days, same_day.totals.prescriptions), (1, 1))
        self.assertFalse(same_day.partial)

    async def test_custom_leap_year_allows_366_days_and_missing_period_remains_unknown(self):
        self.seed(datetime(2024, 1, 1, tzinfo=UTC), [
            (1, "batch.completed", "2024-02-28T16:00:00+00:00", 1),
        ])
        year = self.reader.report(now=NOW, start_date=date(2024, 1, 1), end_date=date(2024, 12, 31)).data
        self.assertEqual((year.days, len(year.daily), year.totals.completed), (366, 366, 1))
        self.assertEqual(year.daily[59].date.isoformat(), "2024-02-29")
        missing = self.reader.report(now=NOW, start_date=date(2023, 12, 1), end_date=date(2023, 12, 31)).data
        self.assertIsNone(missing.totals)
        self.assertTrue(all(day.coverage == "missing" and day.totals is None for day in missing.daily))

    async def test_invalid_custom_ranges_are_rejected_before_any_network_read(self):
        from fastapi import HTTPException
        from app.simulation_statistics import BEIJING
        today = datetime.now(BEIJING).date()
        cases = [
            {"start_date": today}, {"end_date": today},
            {"start_date": today, "end_date": today - timedelta(days=1)},
            {"start_date": today, "end_date": today + timedelta(days=1)},
            {"start_date": today - timedelta(days=366), "end_date": today},
            {"days": 7, "start_date": today, "end_date": today}, {"days": 2},
        ]
        with patch.object(self.reader, "_sync") as sync:
            for kwargs in cases:
                with self.subTest(kwargs=kwargs), self.assertRaises(HTTPException) as error:
                    await self.reader.read(**kwargs)
                self.assertEqual(error.exception.status_code, 422)
            sync.assert_not_called()

    async def test_custom_query_reuses_history_without_resyncing_and_preserves_source_time(self):
        self.seed(datetime(2026, 11, 1, tzinfo=UTC), [
            (1, "batch.completed", "2026-11-09T04:00:00+00:00", 1),
        ], end=datetime.now(UTC))
        with patch.object(self.reader, "_sync") as sync:
            state = await self.reader.read(start_date=date(2026, 11, 9), end_date=date(2026, 11, 10))
        sync.assert_not_called()
        self.assertEqual(state.data.totals.completed, 1)
        self.assertEqual(state.synced_at.timestamp(), self.reader._state()["synced_at"])

    async def test_empty_platform_and_stale_previous_day_have_no_fake_totals(self):
        self.seed(None)
        self.assertIsNone(self.reader.report(1, NOW).data.totals)
        self.seed(datetime(2026, 11, 1, tzinfo=UTC), end=NOW - timedelta(days=1))
        state = self.reader.report(1, NOW)
        self.assertTrue(state.stale)
        self.assertIsNone(state.data.totals)

    async def test_incremental_paging_deduplicates_and_persists_only_statistics(self):
        calls = []
        records = [event(1, "clock.speed_set")]
        records += [event(i + 2, "prescription.created", external_no="private-rx-name") for i in range(5)]
        records += [event(10, "product.dispatched", bags=12, trace_code="private-trace")]
        records += [event(11, "batch.completed", produced_bags=999), event(12, "alarm.raised")]
        self.mock_platform(records, calls)
        with patch("app.simulation_statistics.PAGE_SIZE", 2):
            state = await self.reader.read(1, True)
        self.assertIsNone(state.error)
        # Dates in the fixture are in the same day as the test's fixed report time.
        result = self.reader.report(1, NOW).data.totals
        self.assertEqual((result.prescriptions, result.dispatched_bags, result.completed, result.alarms), (5, 12, 1, 1))
        self.assertTrue(any(c.get("after_id") == "3" for c in calls))
        calls.clear()
        await self.reader.read(1, True)
        self.assertTrue(any(c.get("event_type") == "prescription.created" and c["after_id"] == "6" for c in calls))
        with self.db.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM simulation_events").fetchone()[0], 8)
            dump = "\n".join(db.iterdump())
        self.assertNotIn("private-", dump)
        restored = StatisticsReader(self.settings, self.db)
        self.assertEqual(restored.report(1, NOW).data.totals.dispatched_bags, 12)

    async def test_partial_failure_does_not_commit_events_cursors_or_timestamp(self):
        self.mock_platform([event(1, "prescription.created")])
        await self.reader.read(1, True)
        before = dict(self.reader._state())
        self.mock_platform([event(1, "prescription.created"), event(2, "batch.created")], fail_type="alarm.raised")
        state = await self.reader.read(7, True)
        self.assertTrue(state.stale)
        self.assertNotIn("private", state.model_dump_json())
        self.assertEqual(dict(self.reader._state()), before)
        with self.db.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM simulation_events").fetchone()[0], 1)
        self.assertIsNone(self.reader._client)

    async def test_platform_reset_and_different_source_do_not_mix_old_history(self):
        self.mock_platform([event(1, "prescription.created")])
        await self.reader.read(1, True)
        other = StatisticsReader(replace(self.settings, decoction_base_url="https://another.example"), self.db)
        self.assertIsNone(other.report(7).data)
        self.mock_platform([event(1, "batch.created", "2026-11-13T02:00:00+00:00")])
        await self.reader.read(1, True)
        with self.db.connect() as db:
            rows = db.execute("SELECT event_type FROM simulation_events").fetchall()
        self.assertEqual([r[0] for r in rows], ["batch.created"])
        self.mock_platform([])
        await self.reader.read(1, True)
        self.assertIsNone(self.reader.report(1).data.totals)

    async def test_invalid_cursor_type_timezone_and_bag_count_are_rejected(self):
        cases = [
            {"items": [event(1, "prescription.created")], "next_after_id": 0},
            {"items": [event(1, "prescription.created", "2026-11-13T01:00:00")], "next_after_id": 1},
        ]
        for payload in cases:
            self.reader._new_client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)))
            state = await self.reader.read(1, True)
            self.assertIsNone(state.data)
            self.assertIsNotNone(state.error)
        self.mock_platform([event(1, "product.dispatched", bags=True)])
        state = await self.reader.read(1, True)
        self.assertIsNone(state.data)
        self.assertIn("数量", state.error)

    async def test_concurrent_readers_share_one_sync_and_cached_ranges_need_no_network(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        calls = 0
        async def sync():
            nonlocal calls
            calls += 1
            entered.set()
            await release.wait()
            self.seed(NOW)
        with patch.object(self.reader, "_sync", sync):
            first = asyncio.create_task(self.reader.read(7, True))
            await entered.wait()
            second = asyncio.create_task(self.reader.read(30, True))
            await asyncio.sleep(0)
            release.set()
            await asyncio.gather(first, second)
            self.assertEqual(calls, 1)
            # Seed fresh time to exercise a cached range after a simulated restart.
            self.seed(NOW, end=datetime.now(UTC))
            await self.reader.read(1)
            self.assertEqual(calls, 1)

    async def test_timeout_is_bounded_and_failed_attempt_backs_off(self):
        async def slow():
            await asyncio.sleep(60)
        with patch.object(self.reader, "_sync", side_effect=slow) as sync, patch("app.simulation_statistics.SYNC_TIMEOUT", 0.01):
            state = await self.reader.read(7)
            self.assertIn("超时", state.error)
            await self.reader.read(30)
            self.assertEqual(sync.call_count, 1)

    async def test_transport_recovery_replaces_client_and_keeps_proxy_auth(self):
        settings = replace(self.settings, decoction_proxy_url="http://127.0.0.1:7897",
                           decoction_http_username="user", decoction_http_password="secret", decoction_api_key="key")
        reader = StatisticsReader(settings, self.db)
        with patch("app.simulation_statistics.httpx.AsyncClient") as factory:
            reader._new_client()
            self.assertEqual(factory.call_args.kwargs["proxy"], settings.decoction_proxy_url)
            self.assertFalse(factory.call_args.kwargs["trust_env"])
            self.assertEqual(factory.call_args.kwargs["headers"], {"X-API-Key": "key"})
        bad = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: (_ for _ in ()).throw(httpx.ConnectError("secret"))))
        good = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"items": [], "next_after_id": 0})))
        with patch.object(reader, "_new_client", side_effect=[bad, good]) as factory:
            state = await reader.read(7, True)
        self.assertIsNone(state.error)
        self.assertEqual(factory.call_count, 2)
        self.assertTrue(bad.is_closed and good.is_closed)
