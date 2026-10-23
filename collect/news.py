"""10. 네이버 뉴스 검색 API — 업체별 기사 건수 (spec §10). 8쪽 표 '기사' 열."""
from __future__ import annotations

import requests

from ._env import key

URL = "https://openapi.naver.com/v1/search/news.json"


def count(name: str, city: str | None = None) -> int:
    q = f'"{name}"' + (f" {city}" if city else "")
    r = requests.get(URL, params={"query": q, "display": 10},
                     headers={"X-Naver-Client-Id": key("NAVER_CLIENT_ID"), "X-Naver-Client-Secret": key("NAVER_CLIENT_SECRET")},
                     timeout=10)
    r.raise_for_status()
    items = r.json().get("items", [])
    # 동명 업체 오탐 방지: 제목/요약에 업체명이 그대로 들어간 것만
    return sum(1 for it in items if name in (it.get("title", "") + it.get("description", "")).replace("<b>", "").replace("</b>", ""))
