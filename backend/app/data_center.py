"""Authenticated, read-only views of the configured decoction simulator."""

from typing import Literal

import httpx
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

from .config import Settings


class Device(BaseModel):
    id: str
    name: str
    kind: str
    kind_name: str
    status: str
    batch_id: str | None = None
    capacity_ml: float
    utilization_percent: float


class Batch(BaseModel):
    id: str
    prescription_id: str
    status: str
    current_stage_name: str | None = None
    progress_percent: float
    temperature_c: float
    waiting_reason: str | None = None
    trace_code: str


class Alarm(BaseModel):
    id: str
    device_id: str
    batch_id: str | None = None
    message: str
    status: str
    acknowledged: bool
    created_at: float
    resolved_at: float | None = None


class Clock(BaseModel):
    now: float
    running: bool
    speed: float


class Counts(BaseModel):
    queued: int
    running: int
    paused: int
    completed: int
    cancelled: int


class Summary(BaseModel):
    total_prescriptions: int
    batch_counts: Counts
    dispatched_bags: int
    active_alarms: int
    waiting_batches: int
    bags_per_virtual_hour: float


class Snapshot(BaseModel):
    clock: Clock
    summary: Summary
    devices: list[Device]
    batches: list[Batch]
    alarms: list[Alarm]


class Herb(BaseModel):
    name: str
    unit: str = "g"
    grams_per_dose: float | None = None
    quantity_per_dose: float | None = None
    method: str


class Prescription(BaseModel):
    id: str
    external_no: str
    patient_code: str
    status: str
    priority: int
    doses: int
    bags_per_dose: int
    bag_volume_ml: int
    herbs: list[Herb]
    batch_id: str | None = None
    created_at: float
    created_real_time: str | None = None
    recipe: dict[str, float]
    review: dict | None = None
    note: str = ""


class PrescriptionPage(BaseModel):
    items: list[Prescription]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)


def read_simulation(settings: Settings, path: str, model, params=None):
    headers = {"X-API-Key": settings.decoction_api_key} if settings.decoction_api_key else {}
    auth = (httpx.BasicAuth(settings.decoction_http_username, settings.decoction_http_password)
            if settings.decoction_http_username else None)
    try:
        response = httpx.get(
            f"{settings.decoction_base_url.rstrip('/')}/api/v1/{path}",
            headers=headers, auth=auth, params=params,
            timeout=httpx.Timeout(12, connect=5), trust_env=False,
        )
    except httpx.RequestError:
        raise HTTPException(502, "暂时无法读取仿真平台数据，请稍后重试。") from None
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


def register_data_center_routes(app, require, settings: Settings):
    @app.get("/api/data-center/snapshot", response_model=Snapshot, tags=["数据中心"])
    def snapshot(user=Depends(require("knowledge:read"))):
        return read_simulation(settings, "simulation", Snapshot)

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
