"""5. 네이버 플레이스 — 9쪽 10항목 (spec §5).

    fetch(place_id) -> model.schema.Place 로 바로 들어가는 dict:
      {"photos": 12, "photos_last_year": 2022, "visitor_reviews": 31, "blog_reviews": 8, "replied": 3,
       "reply_rate": 0.10, "rating": 4.6, "last_news_at": "2025-03", "hours_ok": true, "has_kakao": false, ...}

방식: Playwright 로 m.place.naver.com/place/{id}/home · /review/visitor · /feed · /photo 를 열고
      window.__APOLLO_STATE__ 를 파싱. 필드명은 config/place_fields.yaml 로 빼고, 비면 예외.
답글률 = 최근 방문자 리뷰 30개 중 사장님 답글이 달린 수 / 30.
"""
from __future__ import annotations

URLS = {
    "home": "https://m.place.naver.com/place/{id}/home",
    "reviews": "https://m.place.naver.com/place/{id}/review/visitor",
    "feed": "https://m.place.naver.com/place/{id}/feed",
    "photo": "https://m.place.naver.com/place/{id}/photo",
}


def fetch(place_id: str) -> dict:
    raise NotImplementedError("spec §5: __APOLLO_STATE__ 파싱. 반환 키는 model/schema.py Place 와 같게.")
