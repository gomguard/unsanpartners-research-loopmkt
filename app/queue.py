"""아주 단순한 작업 큐 (메모리 dict + 파일). 사용자 3명이면 충분. 필요해지면 sqlite 로."""
from __future__ import annotations

import traceback
import uuid
from datetime import datetime
from pathlib import Path

JOBS: dict[str, dict] = {}
OUT = Path(__file__).resolve().parent.parent / "out"


def submit(**params) -> dict:
    job = {"id": uuid.uuid4().hex[:8], "status": "queued", "created": datetime.now().isoformat(timespec="seconds"), **params}
    JOBS[job["id"]] = job
    return job


def get(job_id: str) -> dict:
    return JOBS.get(job_id, {"status": "unknown"})


def run(job_id: str) -> None:
    from report import build_report
    from render.pdf import make_pdf
    from . import notify

    job = JOBS[job_id]
    job["status"] = "running"
    try:
        r = build_report(job["name"], job["region"], job.get("place_id"), job.get("daangn"),
                         analyst={"name": job["analyst"]} if job.get("analyst") else None)
        OUT.mkdir(exist_ok=True)
        jp = OUT / f"{r.report_id}.json"
        jp.write_text(r.model_dump_json(indent=2), encoding="utf-8")
        pdf = make_pdf(jp, OUT / f"{r.report_id}.pdf")
        job.update(status="done", pdf=str(pdf), json=str(jp))
        notify.done(job)
    except Exception as e:  # noqa: BLE001
        job.update(status="error", error=f"{e}", trace=traceback.format_exc())
        notify.failed(job)
