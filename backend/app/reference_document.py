"""Read-only access to the imported herbal reference and its unchanged DOCX."""
import json
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse

RESOURCE_DIR = Path(__file__).resolve().parents[1] / "resources"


def load_reference_document():
    try:
        document = json.loads((RESOURCE_DIR / "herbal-reference.json").read_text(encoding="utf-8"))
        if not document.get("fullText", "").strip():
            raise ValueError("Empty reference document")
        return document
    except (OSError, ValueError, AttributeError):
        raise HTTPException(503, "基础资料暂时无法读取，请稍后重试") from None


def download_reference_document():
    source = RESOURCE_DIR / "herbal-reference.docx"
    if not source.is_file():
        raise HTTPException(503, "Word 原文件暂时无法读取，请稍后重试")
    document = load_reference_document()
    return FileResponse(source, filename=document["name"], media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
