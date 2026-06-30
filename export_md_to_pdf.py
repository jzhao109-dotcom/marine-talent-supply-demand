#!/usr/bin/env python3
"""Export the final Markdown explanation document to a PDF."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import fitz
import markdown
from PIL import Image


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_MD = ROOT / "海洋人才能力网络三图说明.md"


CSS = """
body {
  font-family: "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", sans-serif;
  color: #263238;
  font-size: 10.5pt;
  line-height: 1.72;
}
h1 {
  font-size: 22pt;
  color: #172532;
  margin: 0 0 18pt 0;
  border-bottom: 1.6pt solid #1f3b57;
  padding-bottom: 10pt;
}
h2 {
  font-size: 15pt;
  color: #1f3b57;
  margin: 22pt 0 9pt 0;
  padding-top: 4pt;
}
p {
  margin: 0 0 8pt 0;
  text-align: justify;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 8pt 0 14pt 0;
  font-size: 8.4pt;
}
th {
  background: #eaf0f5;
  color: #172532;
  font-weight: bold;
}
th, td {
  border: 0.5pt solid #cad4dd;
  padding: 4pt 5pt;
  vertical-align: top;
  word-break: break-all;
}
img {
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
  margin: 10pt auto 12pt auto;
}
ol, ul {
  margin: 5pt 0 10pt 18pt;
  padding-left: 10pt;
}
li {
  margin-bottom: 5pt;
}
code {
  font-family: "Consolas", monospace;
  font-size: 9pt;
}
.page-break {
  page-break-before: always;
}
"""


def resolve_paths() -> tuple[Path, Path]:
    if len(sys.argv) >= 2:
        input_md = Path(sys.argv[1])
        if not input_md.is_absolute():
            input_md = ROOT / input_md
    else:
        input_md = DEFAULT_INPUT_MD

    if len(sys.argv) >= 3:
        output_pdf = Path(sys.argv[2])
        if not output_pdf.is_absolute():
            output_pdf = ROOT / output_pdf
    else:
        output_pdf = input_md.with_suffix(".pdf")
    return input_md.resolve(), output_pdf.resolve()


def make_pdf_image(src: str, input_dir: Path, asset_dir: Path) -> str:
    source = input_dir / src
    if not source.exists():
        return src

    asset_dir.mkdir(exist_ok=True)
    target = asset_dir / (source.stem + "_pdf.jpg")
    with Image.open(source) as im:
        im = im.convert("RGB")
        max_width = 2200
        if im.width > max_width:
            height = round(im.height * max_width / im.width)
            im = im.resize((max_width, height), Image.Resampling.LANCZOS)
        im.save(target, "JPEG", quality=92, optimize=True)
    return target.relative_to(input_dir).as_posix()


def normalize_image_paths(html: str, input_dir: Path, asset_dir: Path) -> str:
    def repl(match: re.Match[str]) -> str:
        before = match.group(1)
        src = match.group(2)
        if src.startswith(("http://", "https://", "file://", "data:")):
            return match.group(0)
        return f'<img{before}src="{make_pdf_image(src, input_dir, asset_dir)}"'

    return re.sub(r'<img([^>]+?)src="([^"]+)"', repl, html)


def insert_page_breaks(md_text: str) -> str:
    for marker in ("\n## 五、", "\n## 八、", "\n## 3.", "\n## 4."):
        md_text = md_text.replace(marker, "\n<div class=\"page-break\"></div>\n" + marker, 1)
    return md_text


def add_page_number(page_num: int, mediabox: fitz.Rect, dev, after: int):
    if not after:
        return
    # Page numbers are intentionally omitted here; keeping the PDF a faithful
    # export of the Markdown content is more important than post-processing.


def export_pdf():
    input_md, output_pdf = resolve_paths()
    input_dir = input_md.parent
    asset_dir = input_dir / "_md_pdf_assets"
    if asset_dir.exists():
        shutil.rmtree(asset_dir)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    md_text = input_md.read_text(encoding="utf-8")
    md_text = insert_page_breaks(md_text)
    html_body = markdown.markdown(md_text, extensions=["tables", "sane_lists"])
    html_body = normalize_image_paths(html_body, input_dir, asset_dir)
    html = f"<!doctype html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"

    archive = fitz.Archive(str(input_dir))
    story = fitz.Story(html, user_css=CSS, archive=archive)

    page = fitz.Rect(0, 0, 595, 842)
    body = fitz.Rect(54, 54, 541, 788)

    def rectfn(_rect_num, _filled):
        return page, body, fitz.Matrix(1, 0, 0, 1, 0, 0)

    writer = fitz.DocumentWriter(str(output_pdf))
    try:
        story.write(writer, rectfn, pagefn=add_page_number)
    finally:
        writer.close()
        if asset_dir.exists():
            shutil.rmtree(asset_dir)
    print(output_pdf)


if __name__ == "__main__":
    export_pdf()
