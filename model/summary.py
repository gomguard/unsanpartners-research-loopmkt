"""수집 결과에서 파생값을 계산한다: 플레이스 판정(○△×), 퍼널 결과, 요약 집계.

render/build.py 가 렌더 직전에 호출한다. JSON에 이미 값이 있으면 건드리지 않는다.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from . import funnel
from .schema import Keyword, Place, PlaceCheck, Report, Summary

CONFIG = Path(__file__).resolve().parent.parent / "config"


def _verdict(value, rule: dict) -> str:
    std = rule.get("standard")
    warn = rule.get("warn")
    lower = rule.get("direction") == "lower_is_better"
    if isinstance(std, bool):
        return "○" if bool(value) else "×"
    if value is None:
        return "×"
    if lower:
        if value <= std:
            return "○"
        if warn is not None and value <= warn:
            return "△"
        return "×"
    if value >= std:
        return "○"
    if warn is not None and value >= warn:
        return "△"
    return "×"


def place_checks(place: Place, daangn: bool | None, rules_path: Path = CONFIG / "place_rules.yaml") -> list[PlaceCheck]:
    rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))["items"]
    ctx = place.model_dump()
    news_days = place.news_days_since
    if news_days is None and place.last_news_at:
        y, m = (place.last_news_at + "-01").split("-")[:2]
        news_days = (date.today() - date(int(y), int(m), 1)).days
    if place.last_news_at:
        y, m = place.last_news_at.split("-")[:2]
        last_news_text = f"{y}년 {int(m)}월"
    else:
        last_news_text = "게시 없음"
    ctx.update(
        photos_last_year=place.photos_last_year or "-",
        reply_rate_pct=round(place.reply_rate * 100),
        news_days_since=news_days,
        last_news_text=last_news_text,
        daangn=daangn,
        google_ok=place.google.exists and place.google.hours_ok,
        google_text=place.google.text,
    )
    out: list[PlaceCheck] = []
    for r in rules:
        key = r["key"]
        value = ctx.get(key)
        now = r["now_format"].format(**ctx) if r.get("now_format") else str(value)
        out.append(PlaceCheck(label=r["label"], now=now, standard=r["standard_text"], verdict=_verdict(value, r)))
    return out


def summarize(all_keywords: list[Keyword]) -> Summary:
    """전체 키워드 목록(캐시)에서 요약 집계. 1위 자리 기준으로 owner_share 를 센다."""
    share = {k: 0 for k in ["사장님", "중개", "체험단", "공업사", "기타", "정보", "빈자리"]}
    for k in all_keywords:
        if k.our_rank == 1:
            share["사장님"] += 1
        elif not k.page1:
            share["빈자리"] += 1
        else:
            share[k.page1[0].type] += 1
    tx = [k for k in all_keywords if k.intent == "거래"]
    return Summary(
        kw_count=len(all_keywords),
        volume_total=sum(k.volume for k in all_keywords),
        tx_kw_count=len(tx),
        tx_volume=sum(k.volume for k in tx),
        our_page1_count=sum(1 for k in all_keywords if k.our_rank),
        empty_count=share["빈자리"],
        owner_share=share,
        flippable_count=share["체험단"] + share["빈자리"],
    )


def finalize(report: Report) -> Report:
    """비어 있는 파생값을 채운다."""
    if not report.place_checks:
        report.place_checks = place_checks(report.place, report.shop.daangn)
    if report.funnel.outputs is None:
        report.funnel.outputs = funnel.compute(report.summary.volume_total, report.funnel.assumptions)
    return report
