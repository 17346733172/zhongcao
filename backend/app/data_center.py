"""Authenticated, read-only views of the configured decoction simulator."""

import logging
from datetime import date, datetime, timezone
from typing import Annotated, Literal

import httpx
from fastapi import Depends, HTTPException, Path, Query

from .config import Settings
from .data_center_models import (Batch, BatchPage, BatchProgressPage, CompletedBatchPage,
                                PrescriptionPage, RecentBatchProgress, Snapshot, SnapshotState)
from .simulation_snapshot import SnapshotReader, validated_response
from .simulation_statistics import StatisticsReader
from .statistics_models import StatisticsState

logger = logging.getLogger("uvicorn.error")


def read_simulation(settings: Settings, path: str, model, params=None):
    headers = {"X-API-Key": settings.decoction_api_key} if settings.decoction_api_key else {}
    auth = (httpx.BasicAuth(settings.decoction_http_username, settings.decoction_http_password)
            if settings.decoction_http_username else None)
    for attempt in range(1, 3):
        try:
            response = httpx.get(
                f"{settings.decoction_base_url.rstrip('/')}/api/v1/{path}",
                headers=headers, auth=auth, params=params,
                timeout=httpx.Timeout(20, connect=10), trust_env=False,
                proxy=settings.decoction_proxy_url or None,
            )
            return validated_response(response, model)
        except httpx.RequestError as error:
            logger.warning("Simulation read attempt %d/2 failed (%s)", attempt, type(error).__name__)
            if attempt == 2:
                detail = ("读取仿真平台超时，请稍后重试。" if isinstance(error, httpx.TimeoutException)
                          else "暂时无法连接仿真平台，请稍后重试。")
                raise HTTPException(502, detail) from None


def register_data_center_routes(app, require, settings: Settings):
    reader = SnapshotReader(settings)
    app.state.data_center_reader = reader
    statistics_reader = StatisticsReader(settings, app.state.database)
    app.state.statistics_reader = statistics_reader

    @app.get("/api/data-center/statistics", response_model=StatisticsState, tags=["数据中心"])
    async def statistics(days: int | None = Query(None, ge=1, le=30), refresh: bool = False,
                         start_date: date | None = None, end_date: date | None = None,
                         user=Depends(require("knowledge:read"))):
        if days not in (None, 1, 7, 30):
            raise HTTPException(422, "统计范围仅支持 1、7、30 天。")
        if start_date is not None or end_date is not None:
            return await statistics_reader.read(days, refresh, start_date=start_date, end_date=end_date)
        return await statistics_reader.read(days if days is not None else 7, refresh)

    @app.get("/api/data-center/snapshot", response_model=SnapshotState, tags=["数据中心"])
    async def snapshot(refresh: bool = False, user=Depends(require("knowledge:read"))):
        await reader.start()
        if refresh:
            reader.request_refresh()
        return reader.state()

    @app.get("/api/data-center/completed-batches", response_model=CompletedBatchPage, tags=["数据中心"])
    def completed_batches(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=200),
                          user=Depends(require("knowledge:read"))):
        page = read_simulation(settings, "batches", BatchPage,
                               {"status": "completed", "offset": offset, "limit": limit})
        if (page.offset != offset or len(page.items) > limit
                or (not page.items and offset < page.total)
                or (page.items and offset + len(page.items) > page.total)
                or any(item.status != "completed" for item in page.items)):
            raise HTTPException(502, "仿真平台已完成批次分页数据异常，请稍后重试。")
        return CompletedBatchPage(**page.model_dump(), fetched_at=datetime.now(timezone.utc))

    @app.get("/api/data-center/recent-batches", response_model=RecentBatchProgress, tags=["数据中心"])
    def recent_batches(limit: int = Query(5, ge=1, le=20), user=Depends(require("knowledge:read"))):
        # The upstream list has no ordering parameter. Read and validate a bounded
        # complete set before sorting, rather than labelling its first page latest.
        items, total = [], None
        for offset in range(0, 1000, 200):
            page = read_simulation(settings, "batches", BatchProgressPage, {"offset": offset, "limit": 200})
            if total is None:
                total = page.total
                if total > 1000:
                    raise HTTPException(502, "批次记录超过本次可核验范围，暂不能确认最近批次；请按具体批次编号查询。")
            if (page.total != total or page.offset != offset
                    or len(page.items) != min(200, total - offset)
                    or len({b.id for b in items + page.items}) != len(items) + len(page.items)):
                raise HTTPException(502, "仿真平台批次分页发生变化，无法确认最近记录，请重新查询。")
            items.extend(page.items)
            if len(items) == total:
                break
        ordered = all(b.created_at is not None for b in items)
        if ordered:
            items.sort(key=lambda b: (b.created_at, b.sequence or 0), reverse=True)
        return RecentBatchProgress(items=items[:limit], total=total, limit=limit,
            fetched_at=datetime.now(timezone.utc), ordered_by_creation=ordered,
            notice=None if ordered else "平台未提供完整创建时间，以下仅为平台返回的批次，不能确认最近顺序。")

    @app.get("/api/data-center/batches/{batch_id}", response_model=Batch, tags=["数据中心"])
    def batch(batch_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,128}$")],
              user=Depends(require("knowledge:read"))):
        return read_simulation(settings, f"batches/{batch_id}", Batch)

    @app.get("/api/data-center/prescriptions", response_model=PrescriptionPage, tags=["数据中心"])
    def prescriptions(
        status: Literal["pending_review", "approved", "rejected"] | None = None,
        offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=200),
        user=Depends(require("knowledge:read")),
    ):
        params = {"offset": offset, "limit": limit}
        if status:
            params["status"] = status
        return read_simulation(settings, "prescriptions", PrescriptionPage, params)
