"""8. Google Places API (New) — 구글 비즈니스 프로필 (spec §8).

    profile("○○공업사", "부천") -> model.schema.GoogleProfile dict
      {"exists": true, "rating": 4.2, "reviews": 13, "photos": 4, "hours_ok": true, "text": "등록, 평점 4.2 · 리뷰 13 · 사진 4"}

소유 확인 여부는 API 가 안 준다 → 사진·영업시간·웹사이트가 있으면 '정보 완성도 ○'로 본다.
"""
from __future__ import annotations

import requests

from ._env import key

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = "places.id,places.displayName,places.rating,places.userRatingCount,places.photos,places.regularOpeningHours,places.websiteUri,places.formattedAddress"


def profile(name: str, city: str) -> dict:
    r = requests.post(URL, json={"textQuery": f"{city} {name}", "languageCode": "ko", "regionCode": "KR"},
                      headers={"X-Goog-Api-Key": key("GOOGLE_PLACES_KEY"), "X-Goog-FieldMask": FIELDS}, timeout=20)
    r.raise_for_status()
    places = r.json().get("places", [])
    if not places:
        return {"exists": False, "rating": None, "reviews": 0, "photos": 0, "hours_ok": False, "text": "미등록 (지도에 자동 생성된 항목만)"}
    p = places[0]
    photos = len(p.get("photos", []))
    hours_ok = bool(p.get("regularOpeningHours"))
    rating = p.get("rating")
    reviews = p.get("userRatingCount", 0)
    return {"exists": True, "rating": rating, "reviews": reviews, "photos": photos, "hours_ok": hours_ok,
            "text": f"등록, 평점 {rating or '-'} · 리뷰 {reviews} · 사진 {photos}" + ("" if hours_ok else " · 영업시간 없음")}
