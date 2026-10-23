"""완료/실패 알림. 슬랙 웹훅(.env SLACK_WEBHOOK)이 있으면 보내고, 없으면 콘솔."""
from __future__ import annotations

import os

import requests


def _send(text: str) -> None:
    url = os.environ.get("SLACK_WEBHOOK")
    if url:
        requests.post(url, json={"text": text}, timeout=10)
    else:
        print("[notify]", text)


def done(job: dict) -> None:
    _send(f"✅ {job['name']} ({job['region']}) 리포트 완료 — /jobs/{job['id']}/pdf")


def failed(job: dict) -> None:
    _send(f"❌ {job['name']} ({job['region']}) 실패 — {job.get('error')}")
