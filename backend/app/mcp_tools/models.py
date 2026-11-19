"""Strict, bounded input schemas shared by MCP and the built-in agent."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ..device_defaults import DeviceKind
from ..schemas import ChatTurn


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class HerbalInput(Input):
    action: Literal['read', 'search', 'ask'] = 'search'
    query: str = Field(default='', max_length=2000)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    history: list[ChatTurn] = Field(default_factory=list, max_length=5)

    @model_validator(mode='after')
    def required_query(self):
        if self.action != 'read' and not self.query.strip():
            raise ValueError('请输入查询内容')
        return self


class DataInput(Input):
    action: Literal['snapshot', 'question', 'statistics', 'prescriptions', 'batch'] = 'snapshot'
    question: str = Field(default='', max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=5)
    refresh: bool = False
    days: Literal[1, 7, 30] | None = None
    start_date: str | None = Field(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    end_date: str | None = Field(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    status: Literal['pending_review', 'approved', 'rejected'] | None = None
    batch_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9_-]{1,128}$')
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=200)

    @model_validator(mode='after')
    def required_fields(self):
        if self.action == 'question' and not self.question.strip():
            raise ValueError('缺少运行问题')
        if self.action == 'batch' and not self.batch_id:
            raise ValueError('缺少批次编号')
        if bool(self.start_date) != bool(self.end_date) or (self.start_date and self.days is not None):
            raise ValueError('日期区间必须成对且不能与 days 同时使用')
        return self


class OverviewInput(Input):
    refresh: bool = False


class ExecutionInput(Input):
    action: Literal['running', 'completed', 'progress', 'status', 'create', 'start', 'pause'] = 'running'
    count: int | None = Field(default=None, ge=1, le=50)
    confirmed: bool = False
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=200)
    refresh: bool = False

    @model_validator(mode='after')
    def check_write(self):
        if self.action == 'progress' and self.limit > 20:
            raise ValueError('最近批次工序查询最多20条')
        if self.action in {'create', 'start', 'pause'} and not self.confirmed:
            raise ValueError('写入必须明确确认')
        if (self.action == 'create') != (self.count is not None):
            raise ValueError('仅生成批次时必须提供数量')
        return self


class PlansInput(Input):
    action: Literal['read', 'save'] = 'read'
    kind: DeviceKind | None = Field(default=None, description='保存时必填，使用英文设备种类枚举，例如包装为 packer。')
    minutes: float | None = Field(default=None, ge=0.1, le=120, allow_inf_nan=False, description='目标分钟数，数值类型。')
    expected_revision: int | None = Field(default=None, ge=0, description='本轮 read 响应的 revision 整数，不能猜测。')
    confirmed: bool = False
    refresh: bool = False

    @model_validator(mode='after')
    def check_write(self):
        if self.action == 'save' and (not self.confirmed or self.kind is None
                or self.minutes is None or self.expected_revision is None):
            raise ValueError('保存须明确确认设备、分钟数和刚读取的修订号')
        if self.action == 'read' and any(value is not None for value in (self.kind, self.minutes, self.expected_revision)):
            raise ValueError('读取不接受保存字段')
        return self
