"""지역 롱테일 키워드 후보 생성 + 의도 분류 (config/keyword_axes.yaml, regions.yaml).

    candidates("부천권") -> ["부천 판금도색", "중동 범퍼 수리 비용", ...]   # 조합 생성 (수천 개)
    intent("부천 범퍼 수리 비용") -> "거래"

흐름: candidates() → autocomplete.expand() 로 표현 보강 → searchad.volumes() → 검색량 10 이상만 남김
     → intent() → cache/regions/{region}/keywords.json  (collect/region.py 가 묶어서 실행)
"""
from __future__ import annotations

import itertools
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parent.parent / "config"


def axes() -> dict:
    return yaml.safe_load((CONFIG / "keyword_axes.yaml").read_text(encoding="utf-8"))


def regions() -> dict:
    return yaml.safe_load((CONFIG / "regions.yaml").read_text(encoding="utf-8"))["regions"]


def candidates(region: str, extra: bool = False) -> list[str]:
    ax = axes()
    reg = regions()[region]
    slots = {
        "region": list(reg["sub_regions"]),
        "part": ax.get("parts", []),
        "service": ax.get("services", []),
        "modifier": ax.get("modifiers", []),
        "model": ax.get("car_models", []),
    }
    out: set[str] = set()
    patterns = list(ax["patterns"]) + (list(ax.get("patterns_extra", [])) if extra else [])
    for pattern in patterns:
        names = [n for n in slots if "{" + n + "}" in pattern]
        for combo in itertools.product(*[slots[n] for n in names]):
            out.add(" ".join(pattern.format(**dict(zip(names, combo))).split()))
    return sorted(out)


def intent(kw: str) -> str:
    ax = axes()["intent"]
    if any(t in kw for t in ax["informational_tokens"]):
        return "정보"
    return "거래"   # 지역+부위/서비스 조합은 기본적으로 맡길 곳을 찾는 검색


def seeds(region: str) -> list[str]:
    """자동완성 씨앗어: 지역 × 핵심 서비스어 (20~30개)."""
    reg = regions()[region]
    core = ["공업사", "판금", "판금도색", "범퍼 수리", "사고차 수리", "문콕"]
    return [f"{p} {c}" for p in reg["sub_regions"][:5] for c in core]
