from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

DoseScope = Literal["per_dose", "total", "unknown"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Medicine(Model):
    name: str = Field(default="", max_length=60)
    dose: str = Field(default="", max_length=32)
    unit: str = Field(default="", max_length=12)
    method: str = Field(default="", max_length=150)
    dose_scope: DoseScope = "unknown"
    source: str = Field(default="", max_length=800)


class Prescription(Model):
    # unknown means that individual rows, rather than a uniform user choice, apply.
    dose_scope: DoseScope = "unknown"
    age: float | None = Field(default=None, ge=0, le=130)
    sex: Literal["male", "female", "unknown"] = "unknown"
    pregnancy: Literal["yes", "no", "unknown"] = "unknown"
    diagnosis: str = Field(default="", max_length=500)
    allergies: str = Field(default="", max_length=500)
    regimen: str = Field(default="", max_length=500)
    doses: int | None = Field(default=None, ge=1, le=365)
    medicines: list[Medicine] = Field(default_factory=list, max_length=100)

    def with_confirmed_scope(self, scope: DoseScope | None = None):
        choice = self.dose_scope if scope is None else scope
        return self.model_copy(update={
            "dose_scope": choice,
            "medicines": [item.model_copy(update={"dose_scope": choice}) if choice != "unknown" else item.model_copy()
                          for item in self.medicines],
        })


class Intent(Model):
    kind: Literal["prescription_check", "not_prescription", "clarify"]
    explanation: str = Field(max_length=300)
    multiple_prescriptions: bool = False


class ReviewRequest(Model):
    prescription: Prescription
    confirmed: Literal[True]


class Finding(Model):
    code: str
    level: Literal["error", "risk", "missing", "review"]
    title: str
    detail: str
    medicines: list[str] = Field(default_factory=list)
    basis: str
    url: str | None = None
    blocking: bool = True


class AuditConclusion(Model):
    status: Literal["passed", "not_passed", "needs_information"]
    result: str
    detail: str
    finding_codes: list[str]
    decision_reasons: list[str]
    note: str = "系统辅助审核结论，须经药师复核确认。"


class ReportSource(Model):
    label: str
    url: str


class MissingInformation(Model):
    field: str
    label: str
    prompt: str


class ReportItem(Model):
    text: str
    lead: str = ""
    children: list[str] = Field(default_factory=list)
    sources: list[ReportSource] = Field(default_factory=list)


class ReportSection(Model):
    number: Literal["3.1", "3.2", "3.3", "3.4", "3.5"]
    title: str
    paragraphs: list[ReportItem] = Field(default_factory=list)
    items: list[ReportItem] = Field(default_factory=list)
    ordered: bool = False
