"""리포트 1건의 데이터 스키마.

리포트 JSON = 이 Report 모델 하나. 템플릿(render/templates)은 이 모델의 필드만 읽는다.
수집기(collect/*)는 각자 맡은 부분만 채우고, model/summary.py 가 파생값을 계산한다.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

OwnerType = Literal["사장님", "중개", "체험단", "공업사", "기타", "정보", "빈자리"]
Verdict = Literal["○", "△", "×"]
Intent = Literal["거래", "정보"]


class Analyst(BaseModel):
    name: str = "[이름]"
    phone: str = "[전화]"
    email: str = "[이메일]"


class Shop(BaseModel):
    name: str                      # "○○공업사"
    region: str                    # 권역 키 (config/regions.yaml): "부천권"
    region_short: str              # 표지·제목에 쓰는 짧은 지역명: "부천"
    sub_regions: list[str] = []    # ["중동", "상동", "송내", "원미"]
    place_id: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    daangn: Optional[bool] = None          # 수동 입력
    daangn_regulars: Optional[int] = None  # 수동 입력


class Owner(BaseModel):
    type: OwnerType
    name: Optional[str] = None     # 익명 표기: "중개업체 A", "B공업사", "체험단"


class Keyword(BaseModel):
    kw: str
    volume: int                    # 월 PC+모바일 검색량
    intent: Intent
    page1: list[Owner] = []        # 1페이지 상위 2개 글의 주인 (빈 리스트 = 빈자리)
    our_rank: Optional[int] = None # 사장님 가게가 1페이지에 있으면 순위
    ai_briefing_present: bool = False
    ai_briefing_cites_us: bool = False

    @property
    def page1_text(self) -> str:
        if not self.page1:
            return "없음 (빈자리)"
        return " · ".join(o.name or o.type for o in self.page1)

    @property
    def our_rank_text(self) -> str:
        return f"{self.our_rank}위" if self.our_rank else "없음"


class Summary(BaseModel):
    kw_count: int
    volume_total: int
    tx_kw_count: int               # 거래 의도 검색어 수
    tx_volume: int                 # 거래 의도 검색량 합
    our_page1_count: int
    empty_count: int
    owner_share: dict[str, int]    # 1위 자리 기준, 합계 = kw_count. 키 = OwnerType
    flippable_count: int           # 체험단 + 빈자리 (사례 글 1편으로 올라가는 자리)

    @property
    def our_page1_pct(self) -> float:
        return round(self.our_page1_count / self.kw_count * 100, 1) if self.kw_count else 0.0

    @property
    def flippable_pct(self) -> int:
        return round(self.flippable_count / self.kw_count * 100) if self.kw_count else 0


class Competitor(BaseModel):
    name: str                      # 익명: "중개업체 A", "B공업사", "체험단 블로그", "사장님 가게"
    type: str                      # "접수센터(중개)", "1급 공업사", "대행사 묶음"
    page1_count: Optional[int] = None
    posts_90d: Optional[str] = None   # "120+", "40", "—"
    reviews: Optional[str] = None
    news: Optional[str] = None
    note: str = ""
    is_us: bool = False


class GoogleProfile(BaseModel):
    exists: bool = False
    rating: Optional[float] = None
    reviews: int = 0
    photos: int = 0
    hours_ok: bool = False
    text: str = "미등록 (지도에 자동 생성된 항목만)"


class Place(BaseModel):
    photos: int = 0
    photos_last_year: Optional[int] = None
    photos_note: str = ""                # ", 작업 사진 없음" 처럼 사진 칸 뒤에 붙는 짧은 메모
    visitor_reviews: int = 0
    blog_reviews: int = 0
    replied: int = 0
    reply_rate: float = 0.0
    rating: Optional[float] = None
    last_news_at: Optional[str] = None   # "2025-03"
    news_days_since: Optional[int] = None
    hours_ok: bool = True
    hours_text: str = "정확, 휴무 표기 있음"
    has_kakao: bool = False
    kakao_text: str = "없음 (전화만)"
    daangn_text: str = "없음"
    google: GoogleProfile = GoogleProfile()
    has_warranty_notice: bool = False
    warranty_text: str = "플레이스 어디에도 없음"
    benchmark_reviews_text: str = "운산자동차 기준 [n]"


class PlaceCheck(BaseModel):
    label: str
    now: str
    standard: str
    verdict: Verdict


class AICitation(BaseModel):
    questions: int = 20
    engines: list[str] = ["naver_ai", "openai", "perplexity", "gemini", "anthropic"]
    runs: int = 3
    mentioned: int = 0             # 질문 20개 중 언급된 수 (3회 중 1회 이상)
    cited: int = 0                 # 질문 20개 중 우리 링크가 출처에 든 수
    target: int = 4
    spot_check: Optional[dict] = None   # 영업 담당 현장 확인 {"questions":3, "mentioned":0, "apps":["chatgpt","perplexity"]}
    table: list[dict] = []


class FunnelAssumptions(BaseModel):
    """기본(base)·보수(conservative)·상단(optimistic) 세 시나리오. 숫자는 model/funnel.py 가 곱한다.

    보수·상단은 각 단계 전환율을 전부 곱한 값이므로, 표에 적는 숫자와 결과(6~12대)가 항상 맞는다.
    """
    share: float = 0.35            # 1페이지 점유
    ctr: float = 0.12
    inquiry: float = 0.15
    intake: float = 0.50
    ticket_krw: int = 850_000
    ticket_is_assumed: bool = True # False 면 사장님 실제 평균으로 교체된 값
    conservative: dict[str, float] = {"share": 0.30, "ctr": 0.11, "inquiry": 0.14, "intake": 0.50}
    optimistic: dict[str, float] = {"share": 0.40, "ctr": 0.14, "inquiry": 0.16, "intake": 0.50}
    notes: dict[str, str] = {      # 10쪽 가정표 '근거' 열
        "share": "빈자리와 체험단 자리의 절반 이상을 90일 내 확보",
        "ctr": "네이버 블로그·플레이스 1페이지 상단 노출 시 운산 자체 실측 범위",
        "inquiry": "사진 1장 접수 창구가 있을 때 기준, 전화만 있으면 절반 이하",
        "intake": "무료 픽업·대차 연계·사전 비용 안내가 있을 때 기준",
        "ticket": "가정값. 사장님 최근 3개월 사고 수리 평균으로 교체",
    }


class FunnelOutputs(BaseModel):
    impressions: int
    clicks: int
    inquiries: int
    intakes: int
    range_low: int                 # 보수 시나리오 입고
    range_high: int                # 상단 시나리오 입고
    revenue_low: int               # 원
    revenue_high: int

    @property
    def range_text(self) -> str:
        return f"{self.range_low}~{self.range_high}대"

    @property
    def revenue_text(self) -> str:
        from .funnel import krw_man
        return f"{krw_man(self.revenue_low)} ~ {krw_man(self.revenue_high)}"


class Funnel(BaseModel):
    assumptions: FunnelAssumptions = FunnelAssumptions()
    outputs: Optional[FunnelOutputs] = None   # 비어 있으면 model/funnel.py 가 계산


class Narrative(BaseModel):
    """LLM이 쓰는 문장. 숫자는 JSON 값만 써야 하며 narrative/validate.py 가 검사한다."""
    conclusions: list[str] = Field(default_factory=list, min_length=0, max_length=3)      # 6쪽 결론 세 줄 (각각 '<b>굵은 머리</b> 본문' 허용)
    competitor_notes: list[str] = Field(default_factory=list)                              # 8쪽 "그래서 사장님 자리는" 3줄
    place_comment: str = ""                                                                # 9쪽 7/10 옆 문장
    timeline: list[str] = Field(default_factory=list)                                      # 10쪽 "언제부터 보이나" 3줄
    cover_sub: str = ""                                                                    # 표지 결론 아래 문장


class Plan(BaseModel):
    ours: list[str] = []           # 11쪽 운산파트너스가 합니다
    yours: list[str] = []          # 11쪽 사장님이 합니다
    timeline: list[str] = []       # 3개: "1~30일 · 기반 — ..."
    price_text: str = "월 [가격]만 원"
    price_note: str = "위 \"운산파트너스가 합니다\" 전부 포함 · 3개월 단위 · 첫 달 실측 리포트로 판단"
    next_steps: list[str] = []     # 3개
    fix_plan: list[str] = []       # 9쪽 2주 안에 고치는 순서 3개 ("1주차 — ...")
    targets: dict[str, str] = {}   # 6쪽 지금→90일: {"page1": "95", "photos": "50장", "reply": "90%", "intake": "6~12대"}


class Report(BaseModel):
    report_id: str
    collected_at: str              # "2026-10-20"
    is_example: bool = False
    analyst: Analyst = Analyst()
    shop: Shop
    keywords: list[Keyword]        # 7쪽 표에 보일 상위 12개 (전체 목록은 cache/)
    summary: Summary
    competitors: list[Competitor]
    place: Place
    place_checks: list[PlaceCheck] = []   # 비어 있으면 model/summary.py 가 place_rules.yaml 로 계산
    ai_citation: AICitation = AICitation()
    funnel: Funnel = Funnel()
    narrative: Narrative = Narrative()
    plan: Plan = Plan()

    @property
    def place_fail_count(self) -> int:
        return sum(1 for c in self.place_checks if c.verdict == "×")

    @property
    def title(self) -> str:
        return f"{self.shop.region_short} {self.shop.name}"

    @property
    def sub_regions_text(self) -> str:
        return " · ".join([self.shop.region] + self.shop.sub_regions)
