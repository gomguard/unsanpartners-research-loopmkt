"""12. 문장 생성 — Claude API (spec §12). 출력은 model.schema.Narrative 의 필드만.

    narrative = write(report)        # dict, validate.check() 통과분만 반환. 실패 시 2회 재생성 후 예외.

규칙: 숫자는 JSON 값만. 새 숫자 금지. 템플릿에는 손대지 않는다. 쪽 번호는 1~7 (render/build.py PG).
"""
from __future__ import annotations

import json

from model.schema import Report

from . import validate

SYSTEM = """당신은 운산파트너스 데이터 분석실의 분석가입니다. 공업사 사장님에게 건네는 진단 리포트의 문장을 씁니다.
규칙:
- 아래 JSON 에 있는 숫자만 씁니다. 새 숫자·추정치·퍼센트를 만들지 않습니다.
- 존댓말, 짧은 문장, 전문용어 없이. "사장님 가게"라고 부릅니다. 경쟁사는 JSON 의 익명 이름 그대로.
- 허용 태그: <b>, <br>, <span class="hot">. 그 외 HTML 금지.
- 쪽 번호를 언급할 때: 요약 2쪽, 검색어 3쪽, 경쟁 4쪽, 플레이스 5쪽, 퍼널 6쪽, 계획 7쪽.
출력은 JSON 하나: {"cover_sub": str, "conclusions": [str×3], "competitor_notes": [str×3], "place_comment": str, "timeline": [str×3]}
- cover_sub: 표지 결론 아래 3문장. 점 그리드(검색어 수)와 주황 점(사장님 가게가 뜨는 검색어 수)을 설명하고 90일 입고 범위를 말합니다.
- conclusions: '<b>굵은 한 줄 결론.</b> 근거 한두 문장' 형식 3개 — 수요 / 누가 먹고 있나 / 뒤집을 수 있는 자리.
- competitor_notes: 1위 경쟁 유형의 약점 / 가져올 수 있는 자리 수 / 못 따라가는 것과 2주 안에 역전되는 것.
- place_comment: '<b>항목 미달.</b>' 로 시작하는 한 문장.
- timeline: '<b>1~30일</b> …', '<b>31~60일</b> …', '<b>61~90일</b> …' 3개."""


def client():
    import anthropic  # pip install anthropic
    return anthropic.Anthropic()   # ANTHROPIC_API_KEY 는 .env → collect/_env.py 가 환경변수로 올린다


def _ask(r: Report, feedback: str = "") -> dict:
    import collect._env  # noqa: F401  (.env 로드)
    payload = r.model_dump(exclude={"narrative"})
    msg = client().messages.create(
        model="claude-sonnet-4-5", max_tokens=1500, system=SYSTEM,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False) + ("\n\n이전 출력의 문제: " + feedback if feedback else "")}],
    )
    text = msg.content[0].text
    text = text[text.find("{"): text.rfind("}") + 1]
    return json.loads(text)


def write(r: Report, retries: int = 2) -> dict:
    feedback = ""
    for _ in range(retries + 1):
        out = _ask(r, feedback)
        ok, problems = validate.check(out, r)
        if ok:
            return out
        feedback = "; ".join(problems)
    raise RuntimeError("문장 검증 실패: " + feedback)
