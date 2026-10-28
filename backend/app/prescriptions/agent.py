from threading import BoundedSemaphore
from typing import TypedDict
from fastapi import HTTPException
from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context
from .files import read_upload, validate_text
from .extraction import classify, extract
from .models import DoseScope, Prescription
from .rules import check_prescription, RULES_VERSION
from .review import build_conclusion
from .narrative import build_sections
from .missing_information import build_missing_information


class State(TypedDict, total=False):
    phase: str
    content: bytes
    filename: str
    text: str
    instruction: str
    dose_scope: DoseScope
    source: dict
    intent: dict
    prescription: dict
    findings: list
    steps: list[str]
    output: dict


class PrescriptionAgent:
    def __init__(self, settings):
        self.settings = settings
        self.slots = BoundedSemaphore(2)
        graph = StateGraph(State)
        graph.add_node("read_upload", self.read)
        graph.add_node("recognize_intent", self.intent)
        graph.add_node("extract_prescription", self.extract)
        graph.add_node("confirm_data", self.preview)
        graph.add_node("check_data", self.check)
        graph.add_node("build_report", self.report)
        graph.add_conditional_edges(START, lambda state: "read_upload" if state["phase"] == "prepare" else "check_data", ["read_upload", "check_data"])
        graph.add_edge("read_upload", "recognize_intent")
        graph.add_conditional_edges("recognize_intent", lambda state: "extract_prescription" if state["intent"]["kind"] == "prescription_check" and not state["intent"]["multiple_prescriptions"] else "confirm_data", ["extract_prescription", "confirm_data"])
        graph.add_edge("extract_prescription", "confirm_data")
        graph.add_edge("confirm_data", END)
        graph.add_edge("check_data", "build_report")
        graph.add_edge("build_report", END)
        self.graph = graph.compile()

    def run(self, state):
        if not self.slots.acquire(blocking=False):
            raise HTTPException(429, "处方检查任务繁忙，请稍后重试。")
        try:
            # No remote traces/checkpoints containing patient data, even when tracing is globally enabled.
            with tracing_context(enabled=False):
                return self.graph.invoke({**state, "steps": []}, config={"recursion_limit": 12})["output"]
        finally:
            self.slots.release()

    def read(self, state):
        source = read_upload(state["content"], state["filename"]) if state.get("content") is not None else validate_text(state.get("text", ""))
        return {"source": source, "steps": ["read_upload"]}

    def intent(self, state):
        if not self.settings.deepseek_api_key:
            raise HTTPException(503, "意图识别需要配置 DeepSeek；仍可使用手动录入进行数据检查。")
        intent = classify(self.settings, state["source"]["text"], state.get("instruction", ""))
        return {"intent": intent.model_dump(), "steps": state["steps"] + ["recognize_intent"]}

    def extract(self, state):
        prescription = extract(self.settings, state["source"]["text"])
        prescription = prescription.with_confirmed_scope(state.get("dose_scope", "unknown"))
        return {"prescription": prescription.model_dump(), "steps": state["steps"] + ["extract_prescription"]}

    def preview(self, state):
        steps = state["steps"] + ["confirm_data"]
        return {"output": {"status": "needs_confirmation" if state.get("prescription") else "needs_clarification", "source": state["source"],
                           "intent": state["intent"], "prescription": state.get("prescription"), "steps": steps,
                           "framework": "LangGraph", "model": self.settings.deepseek_model}}

    def check(self, state):
        prescription = Prescription.model_validate(state["prescription"]).with_confirmed_scope()
        return {"prescription": prescription.model_dump(), "findings": check_prescription(prescription), "steps": ["check_data"]}

    def report(self, state):
        findings = state["findings"]
        counts = {level: sum(item["level"] == level for item in findings) for level in ["error", "risk", "missing", "review"]}
        conclusion = build_conclusion(findings)
        title = {"passed": "本次系统辅助审核通过", "not_passed": "本次系统审核不通过", "needs_information": "处方信息待补充"}[conclusion["status"]]
        prescription = Prescription.model_validate(state["prescription"])
        missing = build_missing_information(prescription, findings)
        sections = build_sections(prescription, findings, conclusion, missing)
        return {"output": {"status": conclusion["status"], "title": title,
                           "prescription": state["prescription"], "findings": findings, "counts": counts,
                           "conclusion": conclusion, "sections": sections,
                           "missing_information": [entry.model_dump() for entry in missing],
                           "steps": state["steps"] + ["build_report"], "framework": "LangGraph", "rules_version": RULES_VERSION,
                           "scope": ["基本信息完整性", "药名、数值、单位和每剂量口径", "重复饮片", "有限十八反与十九畏（人参—五灵脂）配伍规则", "采用参考剂量与特殊煎法"],
                           "limitations": ["仅检查用户已确认的数据；OCR 与模型提取可能有误。", "不是完整现行药典数据库，未覆盖全部十九畏、妊娠禁忌、西药相互作用、诊断适宜性、机构授权和签章。", "通过仅表示本次已覆盖项目的系统辅助审核通过，不代表药师签署或实际调配授权。"]}}
