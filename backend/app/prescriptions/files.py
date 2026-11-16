import base64
from io import BytesIO
from pathlib import Path
from threading import Lock
import warnings
from zipfile import ZipFile, BadZipFile
from fastapi import HTTPException

MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT = 20000
FORMATS = [".txt", ".md", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".webp"]
_pdf_lock = Lock()  # PDFium disallows concurrent calls, including different documents.


def load_image(content):
    from PIL import Image, ImageOps, UnidentifiedImageError
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.format not in {"PNG", "JPEG", "WEBP"}:
                    raise HTTPException(422, "图片实际格式不支持，请使用 PNG、JPG 或 WEBP。")
                if image.width * image.height > 16000000 or getattr(image, "n_frames", 1) > 1:
                    raise HTTPException(422, "请上传不超过 1600 万像素的单帧图片。")
                return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(422, "图片损坏或像素过大，请重新导出后上传。") from None


def vision_image(image, page):
    # Strip file metadata and normalize orientation before sending pixel data.
    image = image.convert("RGB")
    image.thumbnail((8192, 8192))
    stream = BytesIO()
    image.save(stream, "JPEG", quality=95, subsampling=0)
    return {"page": page, "url": "data:image/jpeg;base64," + base64.b64encode(stream.getvalue()).decode("ascii")}


def vision_source(images, method, pages, text="", notes=None):
    if len(text) > MAX_TEXT:
        raise HTTPException(422, "文字超过 2 万字符，请只提供一份处方；不会截断后检查。")
    if sum(len(image["url"]) for image in images) > 40 * 1024 * 1024:
        raise HTTPException(413, "转换后的图片数据过大，请提供更精简的清晰处方文件。")
    return {"text": text, "method": method, "pages": pages, "confidence": None, "images": images,
            "notes": list(notes or []) + ["图片或扫描 PDF 页面将发送至配置的 DeepSeek 云端模型解析。",
                "以下文字由模型转录，未作本地 OCR 独立核验；请以原图为准核对药名、数字、小数点、单位和煎法。"]}


def read_upload(content: bytes, filename: str):
    suffix = Path(filename.replace("\\", "/")).suffix.lower()
    if suffix not in FORMATS:
        raise HTTPException(422, "格式不支持，请选择 TXT、MD、DOCX、PDF、PNG、JPG 或 WEBP。")
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413 if content else 422, "文件为空或超过 10 MB 限制。")
    notes, pages = [], 1
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
                    notes.append("Word 内嵌图片未参与解析；若处方在图片中，请单独上传该图片或扫描 PDF。")
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
                texts, images = [], []
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
                            if min(width, height) <= 0:
                                raise HTTPException(422, "PDF 页面尺寸异常，请重新导出。")
                            scale = min(2, 2400 / max(width, height))
                            if width * height * scale * scale > 16000000:
                                raise HTTPException(422, "PDF 页面尺寸异常，请重新导出。")
                            bitmap = page.render(scale=scale)
                            try:
                                images.append(vision_image(bitmap.to_pil(), index + 1))
                            finally:
                                bitmap.close()
                        texts.append(f"[第 {index + 1} 页]\n{value}")
                    finally:
                        page.close()
                text = "\n\n".join(texts)
                if images:
                    return vision_source(images, "pdf_vision", pages, text)
                method = "pdf_text"
        except pdfium.PdfiumError:
            raise HTTPException(422, "PDF 无法读取或有密码保护，请提供未加密的有效 PDF。") from None
    else:
        return vision_source([vision_image(load_image(content), 1)], "image_vision", 1)
    return validate_text(text, method, notes, pages=pages)


def validate_text(text, method="text", notes=None, confidence=None, pages=1):
    text = text.replace("\x00", "").strip()
    if len(text) < 5:
        raise HTTPException(422, "可读取文字不足，请上传清晰处方或粘贴完整文字。")
    if len(text) > MAX_TEXT:
        raise HTTPException(422, "文字超过 2 万字符，请只提供一份处方；不会截断后检查。")
    return {"text": text, "method": method, "notes": list(notes or []), "confidence": confidence, "pages": pages}
