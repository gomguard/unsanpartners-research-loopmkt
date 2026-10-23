"""2. 네이버 자동완성 — 실제 검색 표현 (spec §2). 비공식 엔드포인트, 가벼움.

    suggest("부천 공업사") -> ["부천 공업사 추천", "부천 공업사 잘하는곳", ...]
"""
from __future__ import annotations

import time

import requests

URL = "https://ac.search.naver.com/nx/ac"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"


def suggest(q: str) -> list[str]:
    r = requests.get(URL, params={"q": q, "st": 100, "r_format": "json", "r_enc": "UTF-8", "frm": "nv"},
                     headers={"User-Agent": UA}, timeout=10)
    r.raise_for_status()
    items = r.json().get("items", [[]])
    return [row[0] for row in items[0]] if items else []


def expand(seeds: list[str], pause: float = 0.5) -> dict[str, list[str]]:
    """씨앗어 20~30개 → 자동완성 표현. 결과는 searchad.volumes() 의 입력으로 넘긴다."""
    out = {}
    for s in seeds:
        out[s] = suggest(s)
        time.sleep(pause)
    return out
