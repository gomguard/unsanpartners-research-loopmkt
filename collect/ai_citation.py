"""9. AI 답변 언급·인용률 — OpenAI · Perplexity · Gemini · Anthropic 웹검색 + 네이버 AI 브리핑 (spec §9).

    measure(shop_name, region_short, shop_domains, questions, runs=3)
      -> model.schema.AICitation dict:
         {"questions": 20, "engines": [...], "runs": 3, "mentioned": n, "cited": m, "target": 4,
          "table": [{"q": "...", "engine": "openai", "run": 1, "mentioned": bool, "cited": bool, "sources": [...]}, ...]}

- mentioned: 답변 본문에 업체명. cited: 출처 URL 에 업체 도메인·블로그·플레이스 ID.
- 질문 20 × 엔진 4 × 3회 = 240콜/주. 주 1회만. cache/shops/{id}/ai_citation.json
- 각주: "AI 인용률은 각사 API 기준, 주 1회 3회 반복 측정". 소비자 앱과 100% 같지 않다.
"""
from __future__ import annotations

from ._env import key

ENGINES = ["openai", "perplexity", "gemini", "anthropic"]


def ask_openai(q: str) -> tuple[str, list[str]]:
    """POST /v1/responses, tools=[{"type":"web_search_preview"}] → (본문, url_citation URL 목록)."""
    raise NotImplementedError("spec §9 OpenAI")


def ask_perplexity(q: str) -> tuple[str, list[str]]:
    """POST https://api.perplexity.ai/chat/completions model=sonar → (본문, citations[])."""
    raise NotImplementedError("spec §9 Perplexity")


def ask_gemini(q: str) -> tuple[str, list[str]]:
    """generateContent tools=[{"google_search":{}}] → (본문, groundingChunks[].web.uri)."""
    raise NotImplementedError("spec §9 Gemini")


def ask_anthropic(q: str) -> tuple[str, list[str]]:
    """messages + tools=[{"type":"web_search_20250305","name":"web_search"}] → (본문, citations[].url)."""
    raise NotImplementedError("spec §9 Anthropic")


ASK = {"openai": ask_openai, "perplexity": ask_perplexity, "gemini": ask_gemini, "anthropic": ask_anthropic}


def measure(shop_name: str, region_short: str, shop_domains: list[str], questions: list[str], runs: int = 3,
            engines: list[str] = ENGINES) -> dict:
    table = []
    for q in questions:
        qq = q.format(region=region_short)
        for eng in engines:
            for run in range(1, runs + 1):
                text, sources = ASK[eng](qq)
                table.append({"q": qq, "engine": eng, "run": run,
                              "mentioned": shop_name in text,
                              "cited": any(d in s for s in sources for d in shop_domains),
                              "sources": sources})
    by_q = {}
    for row in table:
        b = by_q.setdefault(row["q"], {"m": False, "c": False})
        b["m"] |= row["mentioned"]
        b["c"] |= row["cited"]
    return {"questions": len(questions), "engines": engines + ["naver_ai"], "runs": runs,
            "mentioned": sum(1 for b in by_q.values() if b["m"]),
            "cited": sum(1 for b in by_q.values() if b["c"]),
            "target": 4, "table": table}
