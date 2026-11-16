"""One background refresh for all readers, with a validated last-known snapshot."""

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import time

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from .data_center_models import AlarmPage, BatchPage, Dashboard, Snapshot, SnapshotState, Summary

logger = logging.getLogger("uvicorn.error")
REFRESH_TIMEOUT_SECONDS = 45


def validated_response(response, model):
    if response.status_code in {401, 403}:
        raise HTTPException(502, "仿真平台认证失败，请检查后端的 API Key 和网关认证配置。")
    if response.status_code == 404:
        raise HTTPException(502, "仿真平台未提供此数据接口，请检查平台地址与版本。")
    if response.status_code != 200:
        raise HTTPException(502, "仿真平台暂时无法提供数据，请稍后重试。")
    try:
        return model.model_validate(response.json())
    except (ValueError, ValidationError):
        raise HTTPException(502, "仿真平台数据格式异常，请检查平台版本后重试。") from None


class SnapshotReader:
    def __init__(self, settings):
        self.settings = settings
        self.cache_file = settings.database.with_name(settings.database.name + ".simulation-cache.json")
        self.source = hashlib.sha256(settings.decoction_base_url.encode()).hexdigest()
        self.data = None
        self.fetched_at = None
        self.error = None
        self.refreshing = False
        self._worker = None
        self._client = None
        self._wake = asyncio.Event()
        self._load_cache()

    def _load_cache(self):
        try:
            if self.cache_file.stat().st_size > 2 * 1024 * 1024:
                return
            saved = json.loads(self.cache_file.read_text(encoding="utf-8"))
            if saved["source"] != self.source:
                return
            data = Snapshot.model_validate(saved["data"])
            fetched_at = datetime.fromisoformat(saved["fetched_at"])
            if fetched_at.tzinfo is None or fetched_at > datetime.now(timezone.utc):
                return
            self.data, self.fetched_at = data, fetched_at
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError):
            logger.warning("Simulation snapshot cache could not be loaded")

    def _save_cache(self):
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_file.with_suffix(".tmp")
            temporary.write_text(json.dumps({"source": self.source,
                                            "fetched_at": self.fetched_at.isoformat(),
                                            "data": self.data.model_dump()}, ensure_ascii=False), encoding="utf-8")
            temporary.replace(self.cache_file)
        except OSError:
            logger.warning("Simulation snapshot cache could not be saved")

    def _new_client(self):
        return httpx.AsyncClient(
            headers={"X-API-Key": self.settings.decoction_api_key} if self.settings.decoction_api_key else {},
            auth=(httpx.BasicAuth(self.settings.decoction_http_username, self.settings.decoction_http_password)
                  if self.settings.decoction_http_username else None),
            timeout=httpx.Timeout(15, connect=5, pool=2), trust_env=False,
            proxy=self.settings.decoction_proxy_url or None,
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
        )

    async def _close_client(self):
        client, self._client = self._client, None
        if client is not None:
            try:
                async with asyncio.timeout(2):
                    await client.aclose()
            except Exception as error:
                logger.warning("Simulation client cleanup failed (%s)", type(error).__name__)

    async def start(self):
        if self._worker is not None:
            return
        self._client = self._new_client()
        self.refreshing = True
        self._worker = asyncio.create_task(self._run())
        logger.info("Simulation snapshot reader started (clients scoped to one refresh)")

    async def close(self):
        if self._worker is not None:
            self._worker.cancel()
            with suppress(asyncio.CancelledError):
                await self._worker
            self._worker = None
        await self._close_client()

    def request_refresh(self):
        if not self.refreshing:
            self.refreshing = True
            self._wake.set()

    def state(self):
        stale = bool(self.data and (self.error or self.fetched_at < datetime.now(timezone.utc) - timedelta(seconds=30)))
        return SnapshotState(data=self.data, fetched_at=self.fetched_at, refreshing=self.refreshing,
                             stale=stale, error=self.error)

    async def _get(self, path, model, params=None):
        for attempt in range(1, 3):
            try:
                if self._client is None:
                    self._client = self._new_client()
                response = await self._client.get(f"{self.settings.decoction_base_url}/api/v1/{path}", params=params)
                return validated_response(response, model)
            except httpx.RequestError as error:
                logger.warning("Simulation background read %s attempt %d/2 failed (%s); resetting client", path, attempt, type(error).__name__)
                # A failed HTTPS CONNECT/TLS handshake can strand an active pool slot.
                # Never retry through the same failed pool, even if the proxy recovers.
                await self._close_client()
                if attempt == 2:
                    raise HTTPException(502, "暂时无法更新仿真平台数据，后台将自动重试。") from None

    async def _pages(self, path, model, **filters):
        items = []
        offset = 0
        while True:
            page = await self._get(path, model, {**filters, "offset": offset, "limit": 200})
            if page.offset != offset or (not page.items and offset < page.total):
                raise HTTPException(502, "仿真平台分页数据异常，请稍后重试。")
            items.extend(page.items)
            offset += len(page.items)
            if offset >= page.total:
                return items

    async def refresh(self):
        self.refreshing = True
        started = time.monotonic()
        outcome = "cancelled"
        try:
            # Bound the whole refresh, including response bodies and all pages.
            async with asyncio.timeout(REFRESH_TIMEOUT_SECONDS):
                dashboard = await self._get("dashboard", Dashboard)
                alarms = await self._pages("alarms", AlarmPage)
                batches = {}
                for status in ("queued", "running", "paused"):
                    if getattr(dashboard.batch_counts, status):
                        for batch in await self._pages("batches", BatchPage, status=status):
                            batches[batch.id] = batch
                data = Snapshot(clock=dashboard.clock, summary=Summary.model_validate(dashboard.model_dump()),
                                devices=dashboard.devices, batches=list(batches.values()), alarms=alarms)
            self.data = data
            self.fetched_at = datetime.now(timezone.utc)
            self.error = None
            self._save_cache()
            outcome = "success"
        except TimeoutError:
            outcome = "failed"
            self.error = "仿真平台响应较慢，后台将自动重试。"
            logger.warning("Simulation background refresh reached its deadline")
        except HTTPException as error:
            outcome = "failed"
            self.error = error.detail
        except Exception as error:
            outcome = "failed"
            self.error = "暂时无法更新仿真平台数据，后台将自动重试。"
            logger.warning("Simulation background refresh failed (%s)", type(error).__name__)
        finally:
            # Reuse connections within one refresh only. An outage in one cycle must
            # not poison every subsequent poll for the lifetime of the API process.
            await self._close_client()
            self.refreshing = False
            logger.info("Simulation refresh result=%s elapsed_ms=%.0f", outcome, (time.monotonic() - started) * 1000)

    async def _run(self):
        while True:
            self._wake.clear()
            await self.refresh()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=15)
            except TimeoutError:
                pass
