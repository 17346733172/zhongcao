"""Import the supplied reference DOCX without changing its text or source file."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile
from xml.etree import ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{" + NS["w"] + "}"
RESOURCE_DIR = Path(__file__).resolve().parents[1] / "resources"


def paragraph_text(paragraph):
    parts = []
    for node in paragraph.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == W + "tab":
            parts.append("\t")
        elif node.tag in {W + "br", W + "cr"}:
            parts.append("\n")
    return "".join(parts)


def extract_document(source: Path):
    with ZipFile(source) as package:
        body = ET.fromstring(package.read("word/document.xml")).find("w:body", NS)
        if body is None:
            raise ValueError("Word 文档缺少正文")
        # This importer preserves this reference's paragraphs, headings and tables.
        # Refuse unsupported visible content rather than silently dropping it.
        if any(name.startswith("word/media/") for name in package.namelist()):
            raise ValueError("文档包含图片，请先补充图片导入支持")
        for part in ("word/footnotes.xml", "word/endnotes.xml"):
            if part in package.namelist():
                notes = ET.fromstring(package.read(part))
                if any(paragraph_text(p).strip() for p in notes.findall(".//w:p", NS)):
                    raise ValueError("文档包含脚注或尾注，请先补充注释导入支持")
        if any(body.findall(".//w:" + tag, NS) for tag in ("drawing", "pict", "txbxContent", "del", "ins", "numPr", "gridSpan", "vMerge")):
            raise ValueError("文档包含当前导入器不支持的结构，请先检查原文")
        blocks = []
        plain = []
        for element in body:
            if element.tag == W + "p":
                text = paragraph_text(element)
                if not text.strip():
                    continue
                style = element.find("w:pPr/w:pStyle", NS)
                style_name = style.get(W + "val", "") if style is not None else ""
                if style_name in {"Heading1", "Heading2", "Heading3"}:
                    block = {"type": "heading", "level": int(style_name[-1]), "text": text}
                else:
                    block = {"type": "paragraph", "text": text}
                blocks.append(block)
                plain.append(text)
            elif element.tag == W + "tbl":
                rows = []
                for row in element.findall("w:tr", NS):
                    cells = ["\n".join(paragraph_text(p) for p in cell.findall("w:p", NS)) for cell in row.findall("w:tc", NS)]
                    rows.append(cells)
                blocks.append({"type": "table", "rows": rows})
                plain.append("\n".join("\t".join(row) for row in rows))
        full_text = "\n\n".join(plain)
        if not full_text.strip():
            raise ValueError("文档正文为空")
        return {
            "id": "herbal-reference", "name": source.name, "demo": False,
            "excerpt": full_text[:300], "fullText": full_text, "blocks": blocks,
            "downloadUrl": "/api/reference-document/file",
            "sourceSha256": sha256(source.read_bytes()).hexdigest(),
            "paragraphCount": sum(bool(paragraph_text(p).strip()) for p in body.findall(".//w:p", NS)),
            "tableCount": len(body.findall("w:tbl", NS)),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    document = extract_document(args.source)
    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    destination = RESOURCE_DIR / "herbal-reference.docx"
    if args.source.resolve() != destination.resolve():
        copyfile(args.source, destination)
    (RESOURCE_DIR / "herbal-reference.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {document['paragraphCount']} paragraphs and {document['tableCount']} tables.")


if __name__ == "__main__":
    main()
