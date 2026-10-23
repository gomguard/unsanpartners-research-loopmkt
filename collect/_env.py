"""`.env` 로더. 키 이름은 .env.example 과 같다."""
from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load() -> None:
    p = _ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load()


def key(name: str, required: bool = True) -> str | None:
    v = os.environ.get(name)
    if required and not v:
        raise RuntimeError(f".env 에 {name} 이(가) 없습니다. .env.example 을 보세요.")
    return v
