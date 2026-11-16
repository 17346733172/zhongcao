"""Incremental, read-only business-event history, persisted without patient data."""

import asyncio
from datetime import datetime, time as day_time, timedelta, timezone
import hashlib
import logging
import time

import httpx
from fastapi import HTTPException

from .simulation_snapshot import validated_response
from .statistics_models import (
    DailyStatistics, EventPage, StatisticsReport, StatisticsState, StatisticsTotals,
)

logger = logging.getLogger("uvicorn.error")
BEIJING = timezone(timedelta(hours=8))
EVENT_METRICS = {
    "prescription.created": "prescriptions",
    "batch.created": "batches",
    "batch.completed": "completed",
    "product.dispatched": "dispatched_bags",
    "alarm.raised": "alarms",
}
PAGE_SIZE = 1000
SYNC_TIMEOUT = 35


def statistics_range(days=None, start_date=None, end_date=None, now=None):
    today = (now or datetime.now(timezone.utc)).astimezone(BEIJING).date()
    if start_date is not None or end_date is not None:
        if start_date is None or end_date is None:
            raise HTTPException(422, "请选择开始日期和结束日期。")
        if days is not None:
            raise HTTPException(422, "快捷范围与自定义日期不能同时选择。")
        if start_date > end_date:
            raise HTTPException(422, "开始日期不能晚于结束日期。")
        if end_date > today:
            raise HTTPException(422, "结束日期不能晚于今天（北京时间）。")
        if (end_date - start_date).days >= 366:
            raise HTTPException(422, "一次最多查询366天，请缩小时间范围。")
        return start_date, end_date
    days = days if days is not None else 7
    if days not in (1, 7, 30):
        raise HTTPException(422, "快捷范围仅支持1、7、30天。")
    return today - timedelta(days=days - 1), today


class StatisticsReader:
    def __init__(self, settings, database):
        self.settings, self.database = settings, database
        self.source = hashlib.sha256(settings.decoction_base_url.rstrip("/").encode()).hexdigest()
        self.error = None
        self._lock = asyncio.Lock()
        self._last_attempt = float("-inf")
        self._client = None

    def _state(self):
        with self.database.connect() as db:
            return db.execute("SELECT * FROM simulation_history_state WHERE source=?", (self.source,)).fetchone()

    def _new_client(self):
        return httpx.AsyncClient(
            headers={"X-API-Key": self.settings.decoction_api_key} if self.settings.decoction_api_key else {},
            auth=(httpx.BasicAuth(self.settings.decoction_http_username, self.settings.decoction_http_password)
                  if self.settings.decoction_http_username else None),
            proxy=self.settings.decoction_proxy_url or None, trust_env=False,
            timeout=httpx.Timeout(12, connect=5, pool=2),
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=1),
        )

    async def close(self):
        client, self._client = self._client, None
        if client is not None:
            try:
                async with asyncio.timeout(2):
                    await client.aclose()
            except Exception as error:
                logger.warning("Simulation history cleanup failed (%s)", type(error).__name__)

    async def _get(self, params):
        for attempt in range(2):
            try:
                if self._client is None:
                    self._client = self._new_client()
                response = await self._client.get(
                    f"{self.settings.decoction_base_url.rstrip('/')}/api/v1/events", params=params,
                )
                return validated_response(response, EventPage)
            except httpx.RequestError as error:
                logger.warning("Simulation history read failed (%s)", type(error).__name__)
                # A failed proxy TLS handshake must not strand a connection-pool slot.
                await self.close()
                if attempt:
                    raise HTTPException(502, "暂时无法读取平台历史记录，请稍后重试。") from None

    @staticmethod
    def _check_page(page, cursor, event_type=None):
        ids = [event.id for event in page.items]
        if (len(ids) > PAGE_SIZE or ids != sorted(set(ids)) or any(i <= cursor for i in ids)
                or page.next_after_id != (ids[-1] if ids else cursor)
                or (event_type and any(e.type != event_type for e in page.items))):
            raise HTTPException(502, "平台历史记录分页异常，请稍后重试。")

    async def _sync(self):
        # This cutoff precedes the reads. Events arriving during paging are saved but
        # counted only on the next sync, so the reported timestamp is conservative.
        cutoff = datetime.now(timezone.utc).timestamp()
        first = await self._get({"after_id": 0, "limit": 1})
        self._check_page(first, 0)
        if len(first.items) > 1:
            raise HTTPException(502, "平台历史记录分页异常，请稍后重试。")
        earliest = first.items[0].real_time.timestamp() if first.items else None
        origin = (hashlib.sha256(first.items[0].model_dump_json(exclude={"payload"}).encode()).hexdigest()
                  if first.items else "empty")
        saved = self._state()
        reset = saved is None or saved["origin"] != origin
        with self.database.connect() as db:
            cursors = {} if reset else dict(db.execute(
                "SELECT event_type,after_id FROM simulation_event_cursors WHERE source=?", (self.source,),
            ).fetchall())
        rows = []
        for event_type in EVENT_METRICS:
            cursor = cursors.get(event_type, 0)
            if first.items:
                while True:
                    page = await self._get({"after_id": cursor, "limit": PAGE_SIZE, "event_type": event_type})
                    self._check_page(page, cursor, event_type)
                    for event in page.items:
                        amount = event.payload.get("bags") if event_type == "product.dispatched" else 1
                        if type(amount) is not int or amount < 0:
                            raise HTTPException(502, "平台历史配发数量格式异常，请稍后重试。")
                        rows.append((self.source, event.id, event_type, event.real_time.timestamp(), amount))
                    cursor = page.next_after_id
                    if len(page.items) < PAGE_SIZE:
                        break
            cursors[event_type] = cursor
        # Commit events, cursors and timestamp together only after every type succeeds.
        with self.database.connect() as db:
            if reset:
                db.execute("DELETE FROM simulation_events WHERE source=?", (self.source,))
                db.execute("DELETE FROM simulation_event_cursors WHERE source=?", (self.source,))
            db.executemany("INSERT OR IGNORE INTO simulation_events VALUES(?,?,?,?,?)", rows)
            db.executemany("INSERT OR REPLACE INTO simulation_event_cursors VALUES(?,?,?)",
                           [(self.source, kind, cursor) for kind, cursor in cursors.items()])
            db.execute("INSERT OR REPLACE INTO simulation_history_state VALUES(?,?,?,?)",
                       (self.source, origin, earliest, cutoff))

    async def read(self, days=None, refresh=False, *, start_date=None, end_date=None):
        start_date, end_date = statistics_range(days, start_date, end_date)
        requested = time.monotonic()
        async with self._lock:
            saved = self._state()
            age = datetime.now(timezone.utc).timestamp() - saved["synced_at"] if saved else float("inf")
            # Coalesce concurrent forced reads and back off failed reads for 60s.
            if self._last_attempt < requested and (refresh or age >= 60) and (
                    refresh or requested - self._last_attempt >= 60):
                try:
                    async with asyncio.timeout(SYNC_TIMEOUT):
                        await self._sync()
                    self.error = None
                except HTTPException as error:
                    self.error = error.detail
                except TimeoutError:
                    self.error = "同步平台历史记录超时，请重试。"
                except Exception as error:
                    logger.warning("Simulation history sync failed (%s)", type(error).__name__)
                    self.error = "暂时无法同步平台历史记录，请重试。"
                finally:
                    await self.close()
                    self._last_attempt = time.monotonic()
        return self.report(start_date=start_date, end_date=end_date)

    def report(self, days=None, now=None, *, start_date=None, end_date=None):
        now = now or datetime.now(timezone.utc)
        start_date, end_date = statistics_range(days, start_date, end_date, now)
        days = (end_date - start_date).days + 1
        saved = self._state()
        if saved is None:
            return StatisticsState(data=None, synced_at=None, stale=True, error=self.error)
        end = datetime.fromtimestamp(saved["synced_at"], timezone.utc)
        earliest = datetime.fromtimestamp(saved["earliest_at"], timezone.utc) if saved["earliest_at"] is not None else None
        start = datetime.combine(start_date, day_time(), BEIJING)
        end_exclusive = datetime.combine(end_date + timedelta(days=1), day_time(), BEIJING)
        with self.database.connect() as db:
            rows = db.execute("SELECT event_type,occurred_at,amount FROM simulation_events "
                              "WHERE source=? AND occurred_at>=? AND occurred_at<=? AND occurred_at<?",
                              (self.source, start.timestamp(), end.timestamp(), end_exclusive.timestamp())).fetchall()
        daily = []
        for offset in range(days):
            date = start_date + timedelta(days=offset)
            day_start = datetime.combine(date, day_time(), BEIJING)
            day_end = day_start + timedelta(days=1)
            missing = earliest is None or day_end <= earliest or day_start > end
            coverage = "missing" if missing else "partial" if day_start < earliest else "complete"
            daily.append(DailyStatistics(date=date, coverage=coverage,
                                         totals=None if missing else StatisticsTotals()))
        totals = StatisticsTotals() if any(d.totals is not None for d in daily) else None
        for row in rows:
            offset = (datetime.fromtimestamp(row["occurred_at"], BEIJING).date() - start_date).days
            day = daily[offset]
            if day.totals is not None and totals is not None:
                key = EVENT_METRICS[row["event_type"]]
                setattr(day.totals, key, getattr(day.totals, key) + row["amount"])
                setattr(totals, key, getattr(totals, key) + row["amount"])
        report = StatisticsReport(days=days, started_at=start, ended_at=end, earliest_record_at=earliest,
                                  partial=any(d.coverage != "complete" for d in daily), totals=totals, daily=daily)
        return StatisticsState(data=report, synced_at=end, stale=bool(self.error) or (now - end).total_seconds() > 120,
                               error=self.error)
