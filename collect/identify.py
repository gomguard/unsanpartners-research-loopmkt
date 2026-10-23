"""6. 업체 식별 — 업체명 → 후보 목록 (주소·전화·플레이스 ID) (spec §6).

    search("○○공업사", "부천") -> [{"name": "...", "address": "...", "phone": "...", "place_id": "...", "mapx":..., "mapy":...}, ...]

지역검색 API(공식)는 플레이스 ID 를 안 준다 → m.place.naver.com/place/list?query= 에서 첫 결과 ID 를 보강(비공식).
동명 업체가 흔하므로 앱은 후보 중 하나를 영업 담당이 고르게 한다.
"""
from __future__ import annotations

import requests

from ._env import key

LOCAL = "https://openapi.naver.com/v1/search/local.json"


def search(name: str, city: str, display: int = 5) -> list[dict]:
    r = requests.get(LOCAL, params={"query": f"{city} {name}", "display": display},
                     headers={"X-Naver-Client-Id": key("NAVER_CLIENT_ID"), "X-Naver-Client-Secret": key("NAVER_CLIENT_SECRET")},
                     timeout=10)
    r.raise_for_status()
    out = []
    for it in r.json().get("items", []):
        out.append({"name": it["title"].replace("<b>", "").replace("</b>", ""), "address": it.get("roadAddress") or it.get("address"),
                    "phone": it.get("telephone"), "place_id": None, "mapx": it.get("mapx"), "mapy": it.get("mapy")})
    return out


def place_id_for(name: str, address: str) -> str | None:
    """TODO: 모바일 플레이스 검색에서 이름+주소가 맞는 첫 결과의 ID (비공식)."""
    raise NotImplementedError("spec §6: m.place.naver.com/place/list?query= 파싱")
