"""업체 1건 → 리포트 JSON → PDF. (spec §14 '업체 요청' 흐름)

    python -m report "○○공업사" --region 부천권 [--place-id 123] [--daangn yes|no] [--out out/]

지역 캐시(cache/regions/{region}/)가 있어야 한다. 없으면 먼저 `python -m collect.region 부천권`.
아직 스텁인 수집기는 NotImplementedError 를 던진다 — 그 단계는 docs/spec.md 를 보고 채운다.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from collect import keywords as kwmod
from collect._cache import region_dir, shop_dir, cached
from model import summary as summ
from model.schema import Keyword, Owner, Report, Shop
from render.pdf import make_pdf


def build_report(name: str, region: str, place_id: str | None, daangn: bool | None, analyst: dict | None = None) -> Report:
    reg = kwmod.regions()[region]
    city = reg["city"]
    rd = region_dir(region)
    kw_cache = json.loads((rd / "keywords.json").read_text(encoding="utf-8"))
    owners = json.loads((rd / "owners.json").read_text(encoding="utf-8")) if (rd / "owners.json").exists() else {}
    serp = json.loads((rd / "serp.json").read_text(encoding="utf-8")) if (rd / "serp.json").exists() else {}

    # 키워드 전체 → Keyword 모델 (our_rank 는 serp 에서 사장님 업체명/플레이스 ID 로 찾는다)
    all_kw: list[Keyword] = []
    for kw, v in kw_cache.items():
        page1 = [Owner(**o) for o in owners.get(kw, [])]
        our_rank = _our_rank(serp.get(kw), name, place_id)
        all_kw.append(Keyword(kw=kw, volume=v["volume"], intent=v["intent"], page1=page1, our_rank=our_rank))
    all_kw.sort(key=lambda k: (k.intent != "거래", -k.volume))
    s = summ.summarize(all_kw)

    # 업체 단위 수집 (당일 캐시)
    sd = shop_dir(f"{region}-{name}")
    from collect import place as placemod, google_places, news
    place = cached(sd / "place.json", 1, lambda: placemod.fetch(place_id)) if place_id else {}
    google = cached(sd / "google.json", 1, lambda: google_places.profile(name, city))
    news_n = cached(sd / "news.json", 1, lambda: {"count": news.count(name, city)})["count"]
    place["google"] = google
    place["daangn_text"] = "있음" if daangn else "없음"

    r = Report(
        report_id=f"{date.today().isoformat()}-{region}-{name}",
        collected_at=date.today().isoformat(),
        shop=Shop(name=name, region=region, region_short=city, sub_regions=[x for x in reg["sub_regions"] if x != city][:4],
                  place_id=place_id, daangn=daangn),
        keywords=all_kw[:12],
        summary=s,
        competitors=[],          # TODO: owners 집계 → 익명 라벨 → 상위 3 + 사장님 가게 (뉴스 건수 news_n 포함)
        place=place,
    )
    if analyst:
        r.analyst = r.analyst.model_copy(update=analyst)
    r = summ.finalize(r)

    from narrative import writer
    r.narrative = r.narrative.model_copy(update=writer.write(r))
    return r


def _our_rank(serp_row: dict | None, name: str, place_id: str | None) -> int | None:
    if not serp_row:
        return None
    for p in serp_row.get("posts", []):
        if name in (p.get("blog_name") or "") or name in (p.get("title") or ""):
            return p["rank"]
    for p in serp_row.get("places", []):
        if (place_id and p.get("place_id") == place_id) or p.get("name") == name:
            return p["rank"]
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--region", required=True)
    ap.add_argument("--place-id")
    ap.add_argument("--daangn", choices=["yes", "no"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    r = build_report(a.name, a.region, a.place_id, None if a.daangn is None else a.daangn == "yes")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jp = out / f"{r.report_id}.json"
    jp.write_text(r.model_dump_json(indent=2), encoding="utf-8")
    print(make_pdf(jp, out / f"{r.report_id}.pdf"))
