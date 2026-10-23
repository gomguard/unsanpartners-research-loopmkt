"""3. 네이버 모바일 통합검색 크롤링 — 1페이지 주인·사장님 순위·AI 브리핑 (spec §3).

측정 조건 고정: 모바일 UA, 비로그인, 위치 미설정. 운산네트웍스 프록시 풀, IP당 2~3초.

    fetch("부천 판금도색") -> SerpResult(dict):
      {
        "query": "부천 판금도색", "fetched_at": "2026-10-20T03:12:00+09:00",
        "posts": [ {"rank": 1, "blog_id": "xxx", "blog_name": "...", "title": "...", "date": "2024-05-01", "block": "블로그"} ... ],
        "places": [ {"rank": 1, "name": "○○공업사", "place_id": "123"} ... ],
        "ads": ["..."],
        "ai_briefing": {"present": true, "text": "...", "sources": ["https://..."]} | {"present": false}
      }

TODO(구현): Playwright 로 m.search.naver.com 열고 블로그/VIEW/스마트블록·플레이스·파워링크·AI 브리핑 영역을 파싱.
            셀렉터는 자주 바뀌므로 config/serp_selectors.yaml 로 빼고, 0건이면 예외를 올려 알림.
"""
from __future__ import annotations

from datetime import datetime

MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
URL = "https://m.search.naver.com/search.naver?query={q}"


def fetch(query: str, proxy: str | None = None) -> dict:
    raise NotImplementedError("spec §3: Playwright 모바일 통합검색 파서. 반환 형식은 모듈 docstring 참고.")


def fetch_many(queries: list[str], proxies: list[str] | None = None, per_ip_pause: float = 2.5) -> dict[str, dict]:
    """지역 검색어 300~500개. 프록시 풀을 돌려가며 호출. collect/region.py 가 cached() 로 감싼다."""
    out = {}
    for i, q in enumerate(queries):
        proxy = proxies[i % len(proxies)] if proxies else None
        out[q] = fetch(q, proxy=proxy)
    return out


def empty_result(query: str) -> dict:
    return {"query": query, "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "posts": [], "places": [], "ads": [], "ai_briefing": {"present": False}}
