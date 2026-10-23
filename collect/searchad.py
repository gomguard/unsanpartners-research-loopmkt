"""1. 네이버 검색광고 API — 월 검색량 (spec §1).

    volumes(["부천 판금도색", "부천 범퍼 수리 비용", ...]) -> {kw: {"pc": 120, "mobile": 270, "comp": "중간", "rel": [...]}}

- hintKeywords 는 한 번에 최대 5개. 300~500개면 60~100회 호출, 초당 1회면 2분.
- 응답의 relKeyword 는 입력 외 연관어도 돌아온다 → 후보 키워드로 흡수(지역명이 들어간 것만).
- "< 10" 은 5로 치환.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

import requests

from ._env import key

BASE = "https://api.naver.com"


def _headers(method: str, uri: str) -> dict:
    ts = str(round(time.time() * 1000))
    sig = base64.b64encode(
        hmac.new(key("NAVER_AD_SECRET").encode(), f"{ts}.{method}.{uri}".encode(), hashlib.sha256).digest()
    ).decode()
    return {"X-Timestamp": ts, "X-API-KEY": key("NAVER_AD_API_KEY"), "X-Customer": key("NAVER_AD_CUSTOMER_ID"), "X-Signature": sig}


def _num(v) -> int:
    return 5 if isinstance(v, str) and "<" in v else int(v)


def volumes(keywords: list[str], region_token: str | None = None, pause: float = 1.0) -> dict[str, dict]:
    """키워드 → 월 검색량. region_token 을 주면 그 글자가 든 연관어만 후보에 추가한다."""
    out: dict[str, dict] = {}
    uri = "/keywordstool"
    for i in range(0, len(keywords), 5):
        batch = [k.replace(" ", "") for k in keywords[i:i + 5]]   # API는 공백 없는 키워드 기준
        r = requests.get(BASE + uri, headers=_headers("GET", uri),
                         params={"hintKeywords": ",".join(batch), "showDetail": "1"}, timeout=20)
        r.raise_for_status()
        for row in r.json().get("keywordList", []):
            kw = row["relKeyword"]
            if region_token and region_token not in kw and kw not in batch:
                continue
            out[kw] = {"pc": _num(row["monthlyPcQcCnt"]), "mobile": _num(row["monthlyMobileQcCnt"]),
                       "comp": row.get("compIdx"), "from_hint": kw in batch}
        time.sleep(pause)
    return out
