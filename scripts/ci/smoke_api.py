"""Smoke-test a running ARGUS API: one demo assessment end to end, with no cloud credentials.

usage: python scripts/ci/smoke_api.py [BASE_URL]      (default http://127.0.0.1:8000)

Checks /health, submits the Wirecard AG demo scenario, follows its progress stream until the
final status, then fetches the report and checks its tier and where each result came from.
Standard library only, so it runs against the container without installing anything.
"""

from __future__ import annotations

import json
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

REQUEST = {"entity_name": "Wirecard AG", "entity_type": "corporate", "jurisdiction": "DE"}
AGENTS = ("identity", "screening", "corporate", "transaction", "compliance")
EXPECTED_SOURCES = {**dict.fromkeys(AGENTS[:4], "demo_profile"), "compliance": "computed"}


def call(base: str, path: str, body: dict | None = None, timeout: float = 30) -> bytes:
    url = base.rstrip("/") + path
    if urlsplit(url).scheme not in ("http", "https"):
        raise ValueError(f"Not an HTTP URL: {url}")
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    request = Request(url, data=data, headers=headers)  # noqa: S310 - http(s) only, checked
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - http(s) only, checked
        return response.read()


def wait_for_health(base: str, seconds: float = 60) -> None:
    deadline = time.monotonic() + seconds
    while True:
        try:
            if json.loads(call(base, "/health", timeout=2)) == {"status": "ok"}:
                return
        except OSError:
            if time.monotonic() > deadline:
                raise
        time.sleep(1)


def stream_events(base: str, report_id: str) -> list[dict]:
    text = call(base, f"/api/v1/kyc/stream/{report_id}", timeout=120).decode()
    events = []
    for block in text.replace("\r\n", "\n").strip().split("\n\n"):
        data = [line[6:] for line in block.splitlines() if line.startswith("data: ")]
        if data:
            events.append(json.loads(data[0]))
    return events


def smoke(base: str) -> list[str]:
    wait_for_health(base)
    report_id = json.loads(call(base, "/api/v1/kyc/assess", REQUEST))["report_id"]
    events = stream_events(base, report_id)
    report = json.loads(call(base, f"/api/v1/kyc/report/{report_id}"))

    problems = []
    done = {"type": "status", "report_id": report_id, "status": "completed"}
    if not events or events[-1] != done:
        problems.append(f"stream did not end with a completed status: {events[-1:]}")
    completed = {e["agent"] for e in events if e["type"] == "agent_completed"}
    if completed != set(AGENTS):
        problems.append(f"agents completed: {sorted(completed)}")
    if report.get("risk_summary", {}).get("overall_risk_tier") != "HIGH":
        problems.append(f"tier: {report.get('risk_summary')}")
    if report.get("audit_trace", {}).get("agent_sources") != EXPECTED_SOURCES:
        problems.append(f"sources: {report.get('audit_trace', {}).get('agent_sources')}")
    if not report.get("regulatory_triggers"):
        problems.append("no regulatory triggers: the regulations search found nothing")
    return problems


def main(argv: list[str]) -> int:
    base = argv[1] if len(argv) > 1 else "http://127.0.0.1:8000"
    problems = smoke(base)
    print("\n".join(problems) if problems else f"Smoke assessment passed against {base}.")
    return int(bool(problems))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
