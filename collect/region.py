"""밤 배치: 지역 단위 수집 → cache/regions/{region}/ (spec §14).

    python -m collect.region 부천권 [--force]

산출물 (전부 30일 캐시):
  keywords.json   {kw: {"volume": int, "intent": "거래"|"정보"}}        ← keywords + autocomplete + searchad
  serp.json       {kw: naver_serp.fetch() 결과}                         ← naver_serp
  owners.json     {kw: [{"type":..., "name":...}, ...]} 상위 2개 주인    ← classify
  google.json     {kw: google_serp.fetch() 결과} 상위 50 + 질문 20        ← google_serp
"""
from __future__ import annotations

import sys

from . import autocomplete, keywords, searchad
from ._cache import cached, region_dir

MIN_VOLUME = 10


def collect_keywords(region: str, force: bool = False) -> dict:
    d = region_dir(region)

    def fetch():
        cands = set(keywords.candidates(region))
        for sugg in autocomplete.expand(keywords.seeds(region)).values():
            cands.update(sugg)
        city = keywords.regions()[region]["city"]
        vols = searchad.volumes(sorted(cands), region_token=city)
        out = {}
        for kw, v in vols.items():
            total = v["pc"] + v["mobile"]
            if total >= MIN_VOLUME:
                out[kw] = {"volume": total, "intent": keywords.intent(kw)}
        return out

    return cached(d / "keywords.json", 30, fetch, force=force)


def collect_serp(region: str, kws: list[str], force: bool = False) -> dict:
    from . import naver_serp
    d = region_dir(region)
    return cached(d / "serp.json", 30, lambda: naver_serp.fetch_many(kws), force=force)


def run(region: str, force: bool = False) -> None:
    kws = collect_keywords(region, force)
    print(f"[{region}] 키워드 {len(kws)}개, 월 검색량 합계 {sum(v['volume'] for v in kws.values()):,}")
    # TODO: collect_serp → classify → google_serp. 각 단계는 NotImplementedError 를 던지는 스텁부터 채운다.


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python -m collect.region <지역키> [--force]")
    run(sys.argv[1], force="--force" in sys.argv)
