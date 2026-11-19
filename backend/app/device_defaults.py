"""Read and update simulator station defaults without inventing local overrides."""

import asyncio
from datetime import datetime, timezone
import time
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .data_center_models import Dashboard
from .simulation_operations import ensure_success, simulation_request

DeviceKind = Literal["dispenser", "verification", "conveyor", "water", "soaking", "decocter",
                     "filter", "packer", "labeler", "quality", "dispatch", "residue", "washer"]
KINDS = set(DeviceKind.__args__)
LEGACY_NOTICE = "当前仿真平台尚未提供默认用时修改接口，更新平台后可保存；以下仅显示已读取的当前值。"


class DeviceDefault(BaseModel):
    kind: DeviceKind
    name: str
    default_processing_seconds: float = Field(ge=6, le=7200, allow_inf_nan=False)


class DefaultsPage(BaseModel):
    items: list[DeviceDefault]
    revision: int = Field(strict=True, ge=0)


class DefaultsStatus(BaseModel):
    items: list[DeviceDefault]
    revision: int | None
    supported: bool | None
    fetched_at: datetime
    notice: str = ""
    stale: bool = False
    error: str | None = None
    capability_pending: bool = False


class DefaultUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_processing_seconds: float = Field(strict=True, ge=6, le=7200, allow_inf_nan=False)
    expected_revision: int = Field(strict=True, ge=0)


def parse_defaults(response):
    try:
        result = DefaultsPage.model_validate(response.json())
        if len(result.items) != len(KINDS) or {item.kind for item in result.items} != KINDS:
            raise ValueError("Incomplete station defaults")
        return result
    except (ValueError, ValidationError):
        raise HTTPException(502, "平台默认用时数据异常，请重新读取。") from None


def defaults_from_devices(devices):
    items = []
    for kind in sorted(KINDS):
        group = [item for item in devices if item.kind == kind]
        durations = {item.default_processing_seconds for item in group}
        if group and len(durations) == 1 and None not in durations:
            items.append(DeviceDefault(kind=kind, name=group[0].kind_name,
                                       default_processing_seconds=durations.pop()))
    return items


async def read_defaults_path(settings, path):
    # Only GET transport failures are retried, each through a fresh connection.
    for attempt in range(2):
        try:
            return await simulation_request(settings, "GET", path)
        except HTTPException as error:
            if error.status_code != 502 or attempt:
                raise


def register_device_default_routes(app, require, settings):
    lock = asyncio.Lock()
    legacy_until = 0.0

    def cached_legacy(error=None):
        state = app.state.data_center_reader.state()
        if state.data is None or state.fetched_at is None:
            return None
        try:
            items = defaults_from_devices(state.data.devices)
        except (ValueError, ValidationError):
            return None
        return DefaultsStatus(items=items, revision=None,
                              supported=False, fetched_at=state.fetched_at, notice=LEGACY_NOTICE,
                              stale=state.stale or bool(error), error=error or state.error)

    def cached_unknown():
        cached = cached_legacy()
        if cached is None:
            return None
        return cached.model_copy(update={"supported": None, "capability_pending": True,
            "notice": "当前显示数据中心已读取的设备默认用时；修改接口暂时无法确认，15 秒后自动重试，确认前只读。"})

    async def legacy_defaults():
        cached = cached_legacy()
        if cached and not cached.stale:
            return cached
        try:
            response = await read_defaults_path(settings, "dashboard")
            ensure_success(response)
            dashboard = Dashboard.model_validate(response.json())
            return DefaultsStatus(items=defaults_from_devices(dashboard.devices), revision=None,
                                  supported=False, fetched_at=datetime.now(timezone.utc), notice=LEGACY_NOTICE)
        except (ValueError, ValidationError):
            raise HTTPException(502, "平台默认用时数据异常，请重新读取。") from None
        except HTTPException as error:
            if cached:
                return cached_legacy("默认用时更新失败，当前保留上次读取的设备数据。")
            raise HTTPException(502, "暂时无法读取设备默认用时，将自动重试；也可点击重新读取。") from error

    @app.get("/api/simulation/device-defaults", response_model=DefaultsStatus, tags=["测试方案"])
    async def defaults(refresh: bool = False, user=Depends(require("knowledge:read"))):
        nonlocal legacy_until
        try:
            async with asyncio.timeout(40):
                if not refresh and time.monotonic() < legacy_until:
                    return await legacy_defaults()
                response = await read_defaults_path(settings, "device-defaults")
                if response.status_code == 404:
                    legacy_until = time.monotonic() + 60
                    return await legacy_defaults()
                ensure_success(response)
                page = parse_defaults(response)
                legacy_until = 0.0
                return DefaultsStatus(**page.model_dump(), supported=True, fetched_at=datetime.now(timezone.utc))
        except (HTTPException, TimeoutError) as error:
            # Probe failures do not prove lack of support. Shared values may still be
            # displayed, with modification capability explicitly left unknown.
            if time.monotonic() < legacy_until:
                cached = cached_legacy("默认用时更新失败，当前保留上次读取的设备数据。")
                if cached:
                    return cached
            unknown = cached_unknown()
            if unknown:
                return unknown
            if isinstance(error, HTTPException) and error.detail not in {"暂时无法读取仿真平台状态，请重新读取。"}:
                raise
            raise HTTPException(502, "暂时无法读取设备默认用时，将自动重试；也可点击重新读取。") from None

    @app.post("/api/simulation/device-defaults/{kind}", response_model=DefaultsStatus, tags=["测试方案"])
    async def update(kind: DeviceKind, body: DefaultUpdate, user=Depends(require("knowledge:read"))):
        if lock.locked():
            raise HTTPException(409, "正在保存默认用时，请等待完成后再操作。")
        async with lock:
            try:
                response = await simulation_request(settings, "POST", f"device-defaults/{kind}", body.model_dump())
                ensure_success(response, write=True)
                page = parse_defaults(response)
                changed = next(item for item in page.items if item.kind == kind)
                if (page.revision != body.expected_revision + 1
                        or changed.default_processing_seconds != body.default_processing_seconds):
                    raise HTTPException(502, "未能确认保存结果，请重新读取后核对；系统不会自动重复提交。")
                return DefaultsStatus(**page.model_dump(), supported=True, fetched_at=datetime.now(timezone.utc))
            finally:
                app.state.data_center_reader.request_refresh()
