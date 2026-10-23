"""리포트 JSON → HTML 7장 (+ report.html 한 파일).

    python -m render.build data/sample_bucheon.json out/

템플릿은 숫자를 만들지 않는다. 격자·막대 좌표처럼 '그리기 위한' 계산만 여기서 한다.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from model import summary
from model.funnel import krw_man
from model.schema import Report

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
FONT = ROOT / "fonts" / "PretendardVariable.woff2"

PAGES = ["01_cover", "02_summary", "03_demand", "04_competitors", "05_place", "06_opportunity", "07_plan"]
PG = {"cover": 1, "summary": 2, "demand": 3, "competitors": 4, "place": 5, "opportunity": 6, "plan": 7}
TOC = [("한 장 요약", PG["summary"]), ("플레이스·채널 점검", PG["place"]),
       ("차주들이 치는 검색어", PG["demand"]), ("돌리면 얼마나 들어오나", PG["opportunity"]),
       ("그 자리를 누가 먹고 있나", PG["competitors"]), ("90일 안에 하는 일", PG["plan"])]

# 4쪽 와플 색. 순서가 곧 칸을 채우는 순서.
WAFFLE_ORDER = [
    ("사장님", "#E2703A", "사장님 가게"),
    ("중개", "#1C2A76", None),          # None → 경쟁사 이름에서 채움
    ("체험단", "#7A86B5", "체험단 블로그"),
    ("공업사", "#A9B2D1", None),
    ("기타", "#C9CFE0", "기타 업체·광고"),
    ("정보", "#E3E6EF", "보험·정보성 블로그"),
    ("빈자리", None, "빈자리 (공업사 글 없음)"),
]


# ───────── 필터 ─────────

def f_comma(n) -> str:
    return f"{int(n):,}"


def f_pct(x: float) -> str:
    return f"{round(float(x) * 100)}%"


def f_pct1(x: float) -> str:
    """0.7 → '0.7', 33.0 → '33'."""
    x = float(x)
    return f"{x:.1f}" if x < 10 and x != int(x) else f"{int(round(x))}"


def f_man(n: int) -> str:
    return krw_man(int(n))


KOREAN_COUNT = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱", 8: "여덟", 9: "아홉", 10: "열"}


def f_korean_count(n: int) -> str:
    return KOREAN_COUNT.get(int(n), str(n))


# ───────── 그리기용 계산 ─────────

def dot_grid(kw_count: int, hot_count: int, cell: int = 21) -> dict:
    """표지 점 그리드. cols×cols 격자, 남는 칸은 흰 마스크, 앞쪽 hot_count 칸은 주황 점."""
    cols = max(1, math.ceil(math.sqrt(kw_count)))
    masks = [{"x": (i % cols) * cell, "y": (i // cols) * cell} for i in range(kw_count, cols * cols)]
    hot = [{"x": (i % cols) * cell + 3.5, "y": (i // cols) * cell + 3.5} for i in range(min(hot_count, kw_count))]
    return {"cols": cols, "cell": cell, "size": cols * cell, "masks": masks, "hot": hot}


def waffle(share: dict[str, int], labels: dict[str, str], cell: int = 16) -> dict:
    """4쪽 와플. 칸 하나 = 검색어 하나, WAFFLE_ORDER 순서로 채운다."""
    total = sum(share.values())
    cols = max(1, math.ceil(math.sqrt(total)))
    cells, legend, i = [], [], 0
    for key, fill, label in WAFFLE_ORDER:
        n = share.get(key, 0)
        for _ in range(n):
            cells.append({"x": (i % cols) * cell, "y": (i // cols) * cell, "fill": fill, "hollow": fill is None})
            i += 1
        pct = n / total * 100 if total else 0
        legend.append({"key": key, "fill": fill, "hollow": fill is None,
                       "label": label or labels[key], "count": n,
                       "pct": f"{pct:.1f}" if 0 < pct < 1 else f"{round(pct)}"})
    return {"cols": cols, "size": cols * cell, "cells": cells, "legend": legend}


def owner_labels(r: Report) -> dict[str, str]:
    """막대·와플에 쓰는 이름. 중개·공업사는 경쟁 표의 익명 이름을 가져온다."""
    first = lambda pred, default: next((c.name for c in r.competitors if not c.is_us and pred(c)), default)
    return {
        "사장님": "사장님 가게",
        "중개": first(lambda c: "중개" in c.type, "중개업체"),
        "체험단": "체험단 블로그",
        "공업사": first(lambda c: "공업사" in c.type, "경쟁 공업사"),
        "기타": "기타·광고",
        "정보": "보험·정보성 블로그",
        "빈자리": "빈자리",
    }


def targets(r: Report) -> list[dict]:
    """2쪽 '지금 → 90일 뒤' 네 줄. 막대는 항목마다 자기 기준."""
    s, p, o, t = r.summary, r.place, r.funnel.outputs, r.plan.targets
    page1_t = int(t.get("page1", s.flippable_count))
    photos_t = int(str(t.get("photos", "50")).rstrip("장"))
    reply_t = int(str(t.get("reply", "90%")).rstrip("%"))
    clamp = lambda v: max(1, min(100, round(v)))
    return [
        {"label": f"1페이지 검색어 ({s.kw_count}개 중)", "now": str(s.our_page1_count), "target": str(page1_t),
         "now_w": clamp(s.our_page1_count / s.kw_count * 100), "tgt_w": clamp(page1_t / s.kw_count * 100)},
        {"label": "플레이스 사진", "now": f"{p.photos}장", "target": f"{photos_t}장",
         "now_w": clamp(p.photos / photos_t * 100), "tgt_w": 100},
        {"label": "리뷰 답글률", "now": f"{round(p.reply_rate * 100)}%", "target": f"{reply_t}%",
         "now_w": clamp(p.reply_rate * 100), "tgt_w": reply_t},
        {"label": "검색으로 들어오는 입고 / 월", "now": "0~1대", "target": f"{o.range_text}",
         "now_w": 6, "tgt_w": clamp(o.range_high / 16 * 100)},
    ]


def top_owner_desc(r: Report) -> str:
    sh = {k: v for k, v in r.summary.owner_share.items() if k not in ("빈자리", "정보", "사장님")}
    if not sh:
        return "비어 있는 자리"
    key = max(sh, key=sh.get)
    return {"중개": "공장이 없는 접수센터", "체험단": "오래된 체험단 글", "공업사": "경쟁 공업사", "기타": "광고와 기타 업체"}.get(key, key)


# ───────── 렌더 ─────────

def env() -> Environment:
    e = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]),
                    trim_blocks=True, lstrip_blocks=True)
    e.filters.update(comma=f_comma, pct=f_pct, pct1=f_pct1, man=f_man, korean_count=f_korean_count)
    return e


def load(json_path: Path) -> Report:
    r = Report.model_validate(json.loads(Path(json_path).read_text(encoding="utf-8")))
    return summary.finalize(r)


def context(r: Report, font_url: str) -> dict:
    y, m, d = r.collected_at.split("-")
    labels = owner_labels(r)
    return {
        "r": r,
        "font_url": font_url,
        "pg": PG,
        "total": len(PAGES),
        "toc": TOC,
        "period": f"{y}.{m}",
        "month_text": f"{y}년 {int(m)}월",
        "date_text": f"{y}.{m}.{d}",
        "labels": labels,
        "grid": dot_grid(r.summary.kw_count, r.summary.our_page1_count),
        "waffle": waffle(r.summary.owner_share, labels),
        "targets": targets(r),
        "top_owner_desc": top_owner_desc(r),
    }


def render_pages(r: Report, font_url: str) -> list[str]:
    e = env()
    ctx = context(r, font_url)
    return [e.get_template(f"{name}.html").render(**ctx) for name in PAGES]


def build(json_path: Path, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "fonts").mkdir(exist_ok=True)
    shutil.copy(FONT, out_dir / "fonts" / FONT.name)
    font_url = f"fonts/{FONT.name}"

    r = load(Path(json_path))
    e = env()
    shell = e.get_template("_shell.html")
    pages = render_pages(r, font_url)
    for name, html in zip(PAGES, pages):
        (out_dir / f"{name}.html").write_text(shell.render(r=r, pages=[html], font_url=font_url), encoding="utf-8")
    report = out_dir / "report.html"
    report.write_text(shell.render(r=r, pages=pages, font_url=font_url), encoding="utf-8")
    return report


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python -m render.build <report.json> <out_dir>")
    p = build(Path(sys.argv[1]), Path(sys.argv[2]))
    print(p)
