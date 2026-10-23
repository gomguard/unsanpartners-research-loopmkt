"""7. 구글 검색 — SerpAPI (기본) 또는 DataForSEO (spec §7). 지역 상위 50개 + 질문형 20개만.

    fetch("부천 판금도색", location="Bucheon-si, Gyeonggi-do, South Korea")
      -> {"organic": [{"rank":1,"title":..,"link":..,"domain":..}], "local_pack": [{"name":..}], "ai_overview": {"present": bool, "sources": [..]}}
"""
from __future__ import annotations

import requests

from ._env import key


def fetch(query: str, location: str) -> dict:
    r = requests.get("https://serpapi.com/search.json",
                     params={"engine": "google", "q": query, "hl": "ko", "gl": "kr", "location": location,
                             "api_key": key("SERPAPI_KEY")}, timeout=30)
    r.raise_for_status()
    j = r.json()
    ao = j.get("ai_overview") or {}
    return {
        "organic": [{"rank": i + 1, "title": o.get("title"), "link": o.get("link"), "domain": o.get("displayed_link")}
                    for i, o in enumerate(j.get("organic_results", []))],
        "local_pack": [{"name": p.get("title"), "rating": p.get("rating"), "reviews": p.get("reviews")}
                       for p in (j.get("local_results") or {}).get("places", [])] if isinstance(j.get("local_results"), dict)
                      else [{"name": p.get("title")} for p in j.get("local_results", [])],
        "ai_overview": {"present": bool(ao), "sources": [s.get("link") for s in ao.get("references", []) if s.get("link")]},
        "related_questions": [q.get("question") for q in j.get("related_questions", [])],
    }
