"""LLM 문장 검증: 본문 속 숫자는 전부 JSON 에 있는 값이어야 한다. 허용 태그는 <b>, <br>, <span class="hot"> 뿐.

    ok, problems = check(narrative_dict, report)
"""
from __future__ import annotations

import re

from model.schema import Report

ALLOWED_TAGS = re.compile(r"</?(b|br|span(?: class=\"hot\")?)\s*/?>")
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def allowed_numbers(r: Report) -> set[str]:
    """리포트 JSON 에서 나올 수 있는 숫자 문자열의 집합 (원본, 콤마 포함형, 만 원 단위, %)."""
    s, o, a, p = r.summary, r.funnel.outputs, r.funnel.assumptions, r.place
    nums: set[float] = set()
    nums.update([s.kw_count, s.volume_total, s.tx_kw_count, s.tx_volume, s.our_page1_count, s.empty_count,
                 s.flippable_count, s.flippable_pct, s.our_page1_pct])
    nums.update(s.owner_share.values())
    nums.update([o.impressions, o.clicks, o.inquiries, o.intakes, o.range_low, o.range_high,
                 o.revenue_low / 10_000, o.revenue_high / 10_000, a.ticket_krw / 10_000])
    nums.update([round(x * 100) for x in (a.share, a.ctr, a.inquiry, a.intake)])
    nums.update([p.photos, p.visitor_reviews, p.blog_reviews, p.replied, round(p.reply_rate * 100), p.rating or 0])
    nums.update([c.page1_count or 0 for c in r.competitors])
    for c in r.competitors:
        for v in (c.posts_90d, c.reviews, c.news):
            if v and v.replace("+", "").isdigit():
                nums.add(int(v.replace("+", "")))
    nums.update(range(0, 101))                       # 작은 수·퍼센트·일수·주차는 허용
    nums.update([2023, 2024, 2025, 2026, 2027])      # 연도
    nums.update(int(x) for x in r.collected_at.split("-"))
    out = set()
    for n in nums:
        if float(n).is_integer():
            out.add(str(int(n)))
            out.add(f"{int(n):,}")
        else:
            out.add(str(n))
    return out


def check(narrative: dict, r: Report) -> tuple[bool, list[str]]:
    allowed = allowed_numbers(r)
    problems = []
    for field, val in narrative.items():
        texts = val if isinstance(val, list) else [val]
        for t in texts:
            if not isinstance(t, str):
                continue
            stripped = ALLOWED_TAGS.sub("", t)
            if "<" in stripped:
                problems.append(f"{field}: 허용되지 않은 태그 — {t[:60]}")
            for m in NUM.findall(stripped):
                if m not in allowed and m.replace(",", "") not in allowed:
                    problems.append(f"{field}: JSON 에 없는 숫자 '{m}' — {t[:60]}")
    return (not problems), problems
