from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import Lock
import warnings
from zipfile import ZipFile, BadZipFile
from fastapi import HTTPException

MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT = 20000
FORMATS = [".txt", ".md", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".webp"]
_ocr_lock = Lock()
_pdf_lock = Lock()  # PDFium disallows concurrent calls, including different documents.


@lru_cache(maxsize=1)
def ocr_engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def ocr_image(image):
    import numpy as np
    with _ocr_lock:
        result, _ = ocr_engine()(np.asarray(image.convert("RGB")))
    if not result:
        raise HTTPException(422, "没有识别到文字。请上传清晰的印刷处方，或粘贴文字手动核对；手写处方可能无法准确识别。")
    # Preserve table rows instead of separating every OCR cell into a new line.
    rows = []
    for box, text, score in sorted(result, key=lambda row: min(p[1] for p in row[0])):
        y = sum(p[1] for p in box) / 4
        height = max(p[1] for p in box) - min(p[1] for p in box)
        if rows and abs(y - rows[-1][0]) <= max(8, height * .6):
            rows[-1][1].append((min(p[0] for p in box), text))
        else:
            rows.append((y, [(min(p[0] for p in box), text)]))
    text = "\n".join("  ".join(item[1] for item in sorted(row[1])) for row in rows)
    confidence = min(float(item[2]) for item in result)
    return text, confidence


def load_image(content):
    from PIL import Image, ImageOps, UnidentifiedImageError
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(BytesIO(content))
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                raise HTTPException(422, "图片实际格式不支持，请使用 PNG、JPG 或 WEBP。")
            if image.width * image.height > 16000000 or getattr(image, "n_frames", 1) > 1:
                raise HTTPException(422, "请上传不超过 1600 万像素的单帧图片。")
            return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(422, "图片损坏或像素过大，请重新导出后上传。") from None


def read_upload(content: bytes, filename: str):
    suffix = Path(filename.replace("\\", "/")).suffix.lower()
    if suffix not in FORMATS:
        raise HTTPException(422, "格式不支持，请选择 TXT、MD、DOCX、PDF、PNG、JPG 或 WEBP。")
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413 if content else 422, "文件为空或超过 10 MB 限制。")
    notes, confidence, pages = [], None, 1
    if suffix in {".txt", ".md"}:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(422, "文本不是 UTF-8 编码，请转换编码后上传。") from None
        method = "text"
    elif suffix == ".docx":
        from docx import Document
        from docx.text.paragraph import Paragraph
        from lxml.etree import XMLSyntaxError
        try:
            with ZipFile(BytesIO(content)) as archive:
                if len(archive.infolist()) > 1000 or sum(item.file_size for item in archive.infolist()) > 40 * 1024 * 1024:
                    raise HTTPException(422, "Word 解压内容过大，请简化文件后上传。")
                if any(name.startswith("word/media/") for name in archive.namelist()):
                    notes.append("Word 内嵌图片未参与识别；若处方在图片中，请单独上传该图片或扫描 PDF。")
            doc = Document(BytesIO(content))
            parts = []
            for block in doc.iter_inner_content():
                if isinstance(block, Paragraph):
                    parts.append(block.text)
                else:
                    parts.extend(" | ".join(cell.text for cell in row.cells) for row in block.rows)
            text = "\n".join(parts)
        except (BadZipFile, KeyError, ValueError, OSError, XMLSyntaxError):
            raise HTTPException(422, "Word 文件无法读取，请上传有效 DOCX 文件。") from None
        method = "docx"
    elif suffix == ".pdf":
        import pypdfium2 as pdfium
        try:
            with _pdf_lock, pdfium.PdfDocument(content) as document:
                pages = len(document)
                if not 1 <= pages <= 8:
                    raise HTTPException(422, "PDF 每次支持 1–8 页，请仅上传同一份处方。")
                texts, scores = [], []
                for index in range(pages):
                    page = document[index]
                    try:
                        textpage = page.get_textpage()
                        try:
                            value = textpage.get_text_range().strip()
                        finally:
                            textpage.close()
                        if len(value) < 80:
                            width, height = page.get_size()
                            scale = min(2, 2400 / max(width, height))
                            if min(width, height) <= 0 or width * height * scale * scale > 16000000:
                                raise HTTPException(422, "PDF 页面尺寸异常，请重新导出。")
                            bitmap = page.render(scale=scale)
                            try:
                                value, score = ocr_image(bitmap.to_pil())
                                scores.append(score)
                            finally:
                                bitmap.close()
                        texts.append(f"[第 {index + 1} 页]\n{value}")
                    finally:
                        page.close()
                text = "\n\n".join(texts)
                confidence = min(scores) if scores else None
                method = "pdf_ocr" if scores else "pdf_text"
        except pdfium.PdfiumError:
            raise HTTPException(422, "PDF 无法读取或有密码保护，请提供未加密的有效 PDF。") from None
    else:
        text, confidence = ocr_image(load_image(content))
        method = "image_ocr"
    return validate_text(text, method, notes, confidence, pages)


def validate_text(text, method="text", notes=None, confidence=None, pages=1):
    text = text.replace("\x00", "").strip()
    if len(text) < 5:
        raise HTTPException(422, "可读取文字不足，请上传清晰处方或粘贴完整文字。")
    if len(text) > MAX_TEXT:
        raise HTTPException(422, "文字超过 2 万字符，请只提供一份处方；不会截断后检查。")
    notes = list(notes or [])
    if confidence is not None:
        notes.append("图片 / 扫描识别可能有误，请逐项核对药名、数字、小数点、单位和煎法。")
        if confidence < .85:
            notes.append("部分文字识别置信度较低，请对照原文件修改；无法辨认的内容应交由人工核实。")
    return {"text": text, "method": method, "notes": notes, "confidence": confidence, "pages": pages}
