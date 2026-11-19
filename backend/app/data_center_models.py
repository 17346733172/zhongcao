"""Validated projections used by the read-only data center."""

from datetime import datetime
from pydantic import BaseModel, Field


class Device(BaseModel):
    id: str
    name: str
    kind: str
    kind_name: str
    status: str
    batch_id: str | None = None
    capacity_ml: float
    utilization_percent: float
    default_processing_seconds: float | None = None


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


class Dashboard(Summary):
    clock: Clock
    devices: list[Device]


class Snapshot(BaseModel):
    clock: Clock
    summary: Summary
    devices: list[Device]
    batches: list[Batch]
    alarms: list[Alarm]


class SnapshotState(BaseModel):
    data: Snapshot | None
    fetched_at: datetime | None
    refreshing: bool
    stale: bool
    error: str | None


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


class BatchPage(BaseModel):
    items: list[Batch]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)


class CompletedBatchPage(BatchPage):
    fetched_at: datetime


class StageProgress(BaseModel):
    code: str
    name: str
    status: str
    device_id: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    elapsed_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class BatchProgress(Batch):
    created_at: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    sequence: int | None = Field(default=None, ge=0)
    current_stage: str | None = None
    steps: list[StageProgress] = Field(default_factory=list, max_length=200)


class BatchProgressPage(BatchPage):
    items: list[BatchProgress]


class RecentBatchProgress(BaseModel):
    items: list[BatchProgress]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=20)
    fetched_at: datetime
    ordered_by_creation: bool
    notice: str | None = None


class AlarmPage(BaseModel):
    items: list[Alarm]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
