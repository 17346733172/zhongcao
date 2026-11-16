"""Calendar statistics are separate from the simulator's current-state snapshot."""

from datetime import date, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field, StrictInt


class HistoryEvent(BaseModel):
    id: StrictInt = Field(gt=0)
    real_time: AwareDatetime
    type: str
    payload: dict


class EventPage(BaseModel):
    items: list[HistoryEvent]
    next_after_id: StrictInt = Field(ge=0)


class StatisticsTotals(BaseModel):
    prescriptions: int = 0
    batches: int = 0
    completed: int = 0
    dispatched_bags: int = 0
    alarms: int = 0


class DailyStatistics(BaseModel):
    date: date
    coverage: Literal["complete", "partial", "missing"]
    totals: StatisticsTotals | None


class StatisticsReport(BaseModel):
    days: int = Field(ge=1, le=366)
    timezone: str = "Asia/Shanghai"
    started_at: datetime
    ended_at: datetime
    earliest_record_at: datetime | None
    partial: bool
    totals: StatisticsTotals | None
    daily: list[DailyStatistics]


class StatisticsState(BaseModel):
    data: StatisticsReport | None
    synced_at: datetime | None
    stale: bool
    error: str | None
