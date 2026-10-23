"""10쪽 퍼널: 검색 수요 → 1페이지 노출 → 클릭 → 문의 → 입고 → 매출.

가정은 FunnelAssumptions 에, 결과는 FunnelOutputs 에. 숫자는 여기서만 만든다(LLM 금지).

반올림 규칙: 전환율을 끝까지 곱한 뒤 마지막에 한 번만 반올림한다. 단계별 표시값(910, 109, 16)은
그 지점까지의 누적 곱을 반올림한 값이다. 중간에서 반올림해 다시 곱하면 1~2대가 튀기 때문이다.
"""
from __future__ import annotations

from .schema import FunnelAssumptions, FunnelOutputs


def _chain(volume: int, share: float, ctr: float, inquiry: float, intake: float) -> tuple[int, int, int, int]:
    imp = volume * share
    clk = imp * ctr
    inq = clk * inquiry
    intk = inq * intake
    return round(imp), round(clk), round(inq), round(intk)


def compute(volume_total: int, a: FunnelAssumptions) -> FunnelOutputs:
    imp, clk, inq, intk = _chain(volume_total, a.share, a.ctr, a.inquiry, a.intake)
    c, o = a.conservative, a.optimistic
    low = _chain(volume_total, c["share"], c["ctr"], c["inquiry"], c["intake"])[3]
    high = _chain(volume_total, o["share"], o["ctr"], o["inquiry"], o["intake"])[3]
    low = max(min(low, intk), 1)
    high = max(high, intk)
    return FunnelOutputs(
        impressions=imp,
        clicks=clk,
        inquiries=inq,
        intakes=intk,
        range_low=low,
        range_high=high,
        revenue_low=low * a.ticket_krw,
        revenue_high=high * a.ticket_krw,
    )


def krw_man(n: int) -> str:
    """원 → '510만' / '1,020만'."""
    return f"{round(n / 10_000):,}만"


def pct(x: float) -> str:
    return f"{round(x * 100)}%"
