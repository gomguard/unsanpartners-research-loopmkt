"""4. 1페이지 글 주인 분류 — 규칙 + LLM, config/owners.json 영구 캐시 (spec §4).

    owner_type(blog_id, blog_name, titles, shop_name) -> "중개" | "체험단" | "공업사" | "정보" | "광고"

규칙이 못 정하면 Claude API 로 1회 분류하고 owners.json 에 저장한다 (블로그 ID 기준, 다시 묻지 않음).
리포트에는 실명 대신 익명 라벨("중개업체 A", "B공업사")을 쓴다 → anonymize().
"""
from __future__ import annotations

import json
from pathlib import Path

OWNERS = Path(__file__).resolve().parent.parent / "config" / "owners.json"
TYPES = ["중개", "체험단", "공업사", "정보", "광고"]

RULES = {
    "체험단": ["체험단", "협찬", "원고료", "제공받아", "서포터즈", "소정의"],
    "정보": ["손해사정", "보험사", "자동차보험", "보험료", "약관", "법률"],
    "광고": ["파워링크", "광고"],
}


def _load() -> dict:
    return json.loads(OWNERS.read_text(encoding="utf-8"))


def _save(d: dict) -> None:
    OWNERS.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def owner_type(blog_id: str, blog_name: str, titles: list[str], shop_name: str | None = None) -> str:
    db = _load()
    if blog_id in db["entries"]:
        return db["entries"][blog_id]["type"]
    text = " ".join([blog_name, *titles])
    t = None
    if shop_name and shop_name in text:
        t = "공업사"
    else:
        for typ, toks in RULES.items():
            if any(tok in text for tok in toks):
                t = typ
                break
    if t is None:
        t = llm_classify(blog_id, blog_name, titles)
    db["entries"][blog_id] = {"type": t, "name": blog_name, "src": "rule" if t else "llm"}
    _save(db)
    return t


def llm_classify(blog_id: str, blog_name: str, titles: list[str]) -> str:
    """TODO: Claude API (claude-haiku) 에 블로그명·제목 3개를 주고 TYPES 중 하나 + 근거 한 줄.
    프롬프트 요지: '공장이 있는 실제 공업사인가, 접수만 받는 중개인가, 체험단/협찬 글인가, 보험·정보 글인가'."""
    raise NotImplementedError("spec §4: Claude API 분류. narrative/writer.py 의 client() 재사용.")


def anonymize(owners_in_region: list[str], shop_blog_ids: set[str]) -> dict[str, str]:
    """1페이지 점유 상위 순서대로 '중개업체 A', 'B공업사' 같은 익명 라벨을 붙인다. 리포트에 실명 금지."""
    raise NotImplementedError("1위 중개 → '중개업체 A', 상위 공업사 → 'B공업사', 'C공업사' … 순서는 page1_count 내림차순")
