"""리포트 JSON → PDF (A4 7장). Playwright Chromium으로 report.html을 인쇄한다.

    python -m render.pdf data/sample_bucheon.json out/report.pdf

처음 한 번: playwright install chromium
"""
from __future__ import annotations

import sys
from pathlib import Path

from .build import build


def html_to_pdf(html_path: Path, pdf_path: Path) -> Path:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 794, "height": 1123})
        page.goto(Path(html_path).resolve().as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.emulate_media(media="print")
        page.pdf(path=str(pdf_path), width="794px", height="1123px", print_background=True,
                 prefer_css_page_size=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        browser.close()
    return Path(pdf_path)


def make_pdf(json_path: Path, pdf_path: Path) -> Path:
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    report_html = build(Path(json_path), pdf_path.parent)
    return html_to_pdf(report_html, pdf_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python -m render.pdf <report.json> <out.pdf>")
    print(make_pdf(Path(sys.argv[1]), Path(sys.argv[2])))
