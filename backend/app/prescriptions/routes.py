from pathlib import PurePosixPath
from fastapi import Depends, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from .agent import PrescriptionAgent
from .files import MAX_BYTES, MAX_TEXT, FORMATS
from .models import DoseScope, ReviewRequest


def register_prescription_routes(app, require, settings):
    agent = PrescriptionAgent(settings)
    app.state.prescription_agent = agent
    authorized = require("knowledge:read")

    @app.get("/api/prescriptions/status")
    def status(user=Depends(authorized)):
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
        return agent.run({"phase": "check", "prescription": payload.prescription.model_dump()})
