"""영업 담당용 한 페이지 앱 (FastAPI). 업체명 + 지역 + 당근 여부 → 큐 → PDF 링크.

    uvicorn app.main:app --reload --port 8000

사용자 3명, 동시 요청 적음 → 스레드 1개 큐면 충분. 완료되면 notify.py 로 카톡/슬랙.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse

from . import queue

app = FastAPI(title="운산파트너스 진단 리포트")
STATIC = Path(__file__).resolve().parent / "static"


@app.get("/", response_class=HTMLResponse)
def form():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.post("/jobs")
def create(bg: BackgroundTasks, name: str = Form(...), region: str = Form(...),
           place_id: str = Form(""), daangn: str = Form("unknown"), analyst: str = Form("")):
    job = queue.submit(name=name, region=region, place_id=place_id or None,
                       daangn={"yes": True, "no": False}.get(daangn), analyst=analyst)
    bg.add_task(queue.run, job["id"])
    return job


@app.get("/jobs/{job_id}")
def status(job_id: str):
    return queue.get(job_id)


@app.get("/jobs/{job_id}/pdf")
def pdf(job_id: str):
    j = queue.get(job_id)
    if j.get("status") != "done":
        return j
    return FileResponse(j["pdf"], media_type="application/pdf", filename=Path(j["pdf"]).name)
