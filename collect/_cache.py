"""JSON 파일 캐시. 지역 단위는 cache/regions/{region}/, 업체 단위는 cache/shops/{shop_id}/.

    data = cached(region_dir("부천권") / "volumes.json", ttl_days=30, fetch=lambda: searchad.volumes(...))
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")
ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"


def _slug(s: str) -> str:
    return re.sub(r"[^\w가-힣-]+", "_", s).strip("_")


def region_dir(region: str) -> Path:
    p = CACHE / "regions" / _slug(region)
    p.mkdir(parents=True, exist_ok=True)
    return p


def shop_dir(shop_id: str) -> Path:
    p = CACHE / "shops" / _slug(shop_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cached(path: Path, ttl_days: float, fetch: Callable[[], T], force: bool = False) -> T:
    """path 가 ttl 안에 있으면 읽고, 아니면 fetch() 를 호출해 저장한다. ttl_days=0 → 항상 새로."""
    if not force and path.exists() and ttl_days > 0:
        age_days = (time.time() - path.stat().st_mtime) / 86400
        if age_days <= ttl_days:
            return json.loads(path.read_text(encoding="utf-8"))
    data = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
