"""Authenticated controls for the configured process simulator (never physical devices)."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Literal

import httpx
from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

logger = logging.getLogger("uvicorn.error")
UNCERTAIN = "未能确认操作结果，请先查看平台状态与批次数量，确认后再操作；系统不会自动重复提交。"


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int = Field(strict=True, ge=1, le=50)


class SimulationClock(BaseModel):
    now: float = Field(ge=0, allow_inf_nan=False)
    running: StrictBool
    speed: Literal[1]


class ClockStatus(BaseModel):
    clock: SimulationClock
    fetched_at: datetime


class DashboardClock(BaseModel):
    clock: SimulationClock


class ScenarioResult(BaseModel):
    count: int = Field(strict=True, ge=1, le=50)
    batch_ids: list[str] = Field(min_length=1, max_length=50)


class OperationResult(BaseModel):
    action: Literal["scenarios", "start", "pause"]
    fetched_at: datetime
    clock: SimulationClock | None = None
    count: int | None = None
    batch_ids: list[str] = Field(default_factory=list)


async def simulation_request(settings, method, path, payload=None):
    """Each command is sent once: scenario creation is not idempotent upstream."""
    auth = (httpx.BasicAuth(settings.decoction_http_username, settings.decoction_http_password)
            if settings.decoction_http_username else None)
    try:
        async with asyncio.timeout(20):
            async with httpx.AsyncClient(
                headers={"X-API-Key": settings.decoction_api_key} if settings.decoction_api_key else {},
                auth=auth, proxy=settings.decoction_proxy_url or None, trust_env=False,
                timeout=httpx.Timeout(15, connect=5, write=5, pool=2),
            ) as client:
                return await client.request(method, f"{settings.decoction_base_url}/api/v1/{path}",
                                            **({"json": payload} if payload is not None else {}))
    except (httpx.RequestError, TimeoutError) as error:
        logger.warning("Simulation %s %s failed (%s)", method, path, type(error).__name__)
        detail = UNCERTAIN if method == "POST" else "暂时无法读取仿真平台状态，请重新读取。"
        raise HTTPException(502, detail) from None


def ensure_success(response, *, write=False):
    if response.status_code in {401, 403}:
        raise HTTPException(502, "仿真平台认证失败，请检查后端 API Key 和网关认证配置。")
    if response.status_code == 404:
        raise HTTPException(502, "仿真平台未提供此操作接口，请检查平台地址与版本。")
    if response.status_code == 409:
        raise HTTPException(409, "仿真平台当前状态不允许此操作，请重新读取状态后再操作。")
    if response.status_code not in {200, 201}:
        raise HTTPException(502, UNCERTAIN if write else "仿真平台暂时无法提供运行状态，请重新读取。")


def register_simulation_routes(app, require, settings):
    control_lock = asyncio.Lock()

    @app.get("/api/simulation/status", response_model=ClockStatus, tags=["仿真控制"])
    async def status(user=Depends(require("knowledge:read"))):
        response = await simulation_request(settings, "GET", "dashboard")
        ensure_success(response)
        try:
            clock = DashboardClock.model_validate(response.json()).clock
        except (ValueError, ValidationError):
            raise HTTPException(502, "仿真平台状态格式异常，请检查平台版本。") from None
        return ClockStatus(clock=clock, fetched_at=datetime.now(timezone.utc))

    async def operate(action, payload=None):
        if control_lock.locked():
            raise HTTPException(409, "正在执行另一项仿真操作，请等待完成后再操作。")
        async with control_lock:
            try:
                response = await simulation_request(settings, "POST", f"simulation/{action}", payload)
                ensure_success(response, write=True)
                result = OperationResult(action=action, fetched_at=datetime.now(timezone.utc))
                try:
                    if action == "scenarios":
                        created = ScenarioResult.model_validate(response.json())
                        if (created.count != payload["count"] or len(created.batch_ids) != created.count
                                or len(set(created.batch_ids)) != created.count or any(not item for item in created.batch_ids)):
                            raise ValueError("Unconfirmed scenario result")
                        result.count, result.batch_ids = created.count, created.batch_ids
                    else:
                        result.clock = SimulationClock.model_validate(response.json())
                        if result.clock.running != (action == "start"):
                            raise ValueError("Unconfirmed clock state")
                except (ValueError, ValidationError):
                    raise HTTPException(502, UNCERTAIN) from None
                return result
            finally:
                # A timed-out write may still have reached the simulator.
                app.state.data_center_reader.request_refresh()

    @app.post("/api/simulation/scenarios", response_model=OperationResult, tags=["仿真控制"])
    async def scenarios(body: ScenarioRequest, user=Depends(require("knowledge:read"))):
        return await operate("scenarios", {"count": body.count})

    @app.post("/api/simulation/start", response_model=OperationResult, tags=["仿真控制"])
    async def start(user=Depends(require("knowledge:read"))):
        return await operate("start", {"speed": 1})

    @app.post("/api/simulation/pause", response_model=OperationResult, tags=["仿真控制"])
    async def pause(user=Depends(require("knowledge:read"))):
        return await operate("pause")
