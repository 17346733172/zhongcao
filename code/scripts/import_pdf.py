"""Export the supplied PDF to Markdown using its verified existing layout map.

This is a one-time importer for this specific PDF, not a general PDF upload API.
The layout map is accepted only if EVERY non-whitespace PDF character matches,
apart from repeated table headers across page breaks.
"""
import argparse
from difflib import SequenceMatcher
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import pypdfium2 as pdfium

PROJECT = Path(__file__).resolve().parents[2]


def compact(text):
    return re.sub(r"\s+", "", text)


def import_pdf(source, destination, layout):
    document = json.loads(layout.read_text(encoding="utf-8"))
    blocks = document["blocks"]
    pdf = pdfium.PdfDocument(source)
    pages = []
    try:
        page_count = len(pdf)
        for page in pdf:
            text_page = page.get_textpage()
            try:
                pages.append(re.sub(r"第\s*\d+\s*页\s*/\s*共\s*\d+\s*页", "", text_page.get_text_range()))
            finally:
                text_page.close()
                page.close()
    finally:
        pdf.close()
    pdf_text = compact("".join(pages))
    layout_text = compact("".join("".join("".join(row) for row in b["rows"])
                                 if b["type"] == "table" else b["text"] for b in blocks))
    headers = {compact("".join(b["rows"][0])) for b in blocks if b["type"] == "table"}
    repeated_headers = []
    for operation, a, b, _c, _d in SequenceMatcher(None, pdf_text, layout_text, autojunk=False).get_opcodes():
        if operation == "equal":
            continue
        if operation != "delete" or pdf_text[a:b] not in headers:
            raise ValueError("PDF 正文与章节模板不一致；停止转换，不能复用这份结构化模板。")
        repeated_headers.append(pdf_text[a:b])
    markdown = []
    for index, block in enumerate(blocks):
        if block["type"] == "heading":
            markdown.append("#" * min(block["level"] + 1, 6) + " " + block["text"])
        elif block["type"] == "table":
            rows = block["rows"]
            for row_index, row in enumerate(rows):
                markdown.append("| " + " | ".join(cell.replace("|", "\\|").replace("\n", "<br>") for cell in row) + " |")
                if row_index == 0:
                    markdown.append("| " + " | ".join("---" for _ in row) + " |")
            markdown.append("")
        else:
            markdown.append(("# " if index == 0 else "") + block["text"])
        if block["type"] != "table":
            markdown.append("")
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / (source.stem + ".md")
    output.write_text("\n".join(markdown).strip() + "\n", encoding="utf-8")
    pdf_copy = destination / source.name
    if source.resolve() != pdf_copy.resolve():
        shutil.copyfile(source, pdf_copy)
    metadata = {"source": source.name, "sha256": sha256(source.read_bytes()).hexdigest(),
                "pages": page_count, "markdown": output.name,
                "markdownSha256": sha256(output.read_bytes()).hexdigest(),
                "verifiedNonWhitespaceCharacters": len(layout_text),
                "tables": sum(b["type"] == "table" for b in blocks),
                "removedRepeatedTableHeaders": repeated_headers,
                "verification": "Exact text match; only whitespace, page footers and repeated table headers removed."}
    output.with_suffix(".source.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, default=PROJECT / "code" / "data")
    parser.add_argument("--layout", type=Path, default=PROJECT / "backend" / "resources" / "herbal-reference.json")
    args = parser.parse_args()
    import_pdf(args.pdf, args.output, args.layout)
