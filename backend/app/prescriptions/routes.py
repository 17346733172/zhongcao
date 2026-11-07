from pathlib import PurePosixPath
from uuid import uuid4
from fastapi import BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from .agent import PrescriptionAgent
from .files import MAX_BYTES, MAX_TEXT, FORMATS, warm_ocr
from ..integrations.decoction import upload_to_simulation
from .models import DoseScope, ReviewRequest, SimulationUploadRequest, SimulationUploadResult


def register_prescription_routes(app, require, settings):
    agent = PrescriptionAgent(settings)
    app.state.prescription_agent = agent
    authorized = require("knowledge:read")

    @app.get("/api/prescriptions/status")
    def status(background_tasks: BackgroundTasks, user=Depends(authorized)):
        if settings.deepseek_api_key:
            background_tasks.add_task(warm_ocr)
        return {"framework": "LangGraph", "ai_configured": bool(settings.deepseek_api_key),
                "formats": FORMATS, "max_bytes": MAX_BYTES, "max_text": MAX_TEXT, "max_pdf_pages": 8,
                "ocr": "RapidOCR（本地 CPU）", "persistence": "none"}

    @app.post("/api/prescriptions/prepare")
    async def prepare(file: UploadFile | None = File(None), text: str = Form(""),
                      instruction: str = Form("检查这份中药饮片处方的数据与配伍疑点"),
                      dose_scope: DoseScope = Form("unknown"), user=Depends(authorized)):
        if len(instruction) > 500 or len(text) > MAX_TEXT:
            raise HTTPException(422, "检查说明最多 500 字，处方文字最多 2 万字符。")
        if bool(file) == bool(text.strip()):
            if file:
                await file.close()
            raise HTTPException(422, "每次请选择一个文件或粘贴一份文字，不要同时提交。")
        state = {"phase": "prepare", "instruction": instruction, "dose_scope": dose_scope}
        if file:
            try:
                content = await file.read(MAX_BYTES + 1)
            finally:
                await file.close()
            state.update(content=content, filename=PurePosixPath((file.filename or "").replace("\\", "/")).name)
        else:
            state["text"] = text
        return await run_in_threadpool(agent.run, state)

    @app.post("/api/prescriptions/check")
    def check(payload: ReviewRequest, user=Depends(authorized)):
        if not payload.prescription.medicines:
            raise HTTPException(422, "请至少录入一味药，并核对后确认。")
        report = agent.run({"phase": "check", "prescription": payload.prescription.model_dump()})
        return {**report, "simulation_upload_id": str(uuid4())}

    @app.post("/api/prescriptions/simulation", response_model=SimulationUploadResult,
              tags=["处方仿真对接"], summary="上传已核对处方到煎药仿真平台")
    def upload(payload: SimulationUploadRequest, user=Depends(authorized)):
        return upload_to_simulation(settings, payload)
