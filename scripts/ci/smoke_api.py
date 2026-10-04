"""Smoke-test a running ARGUS API: one demo assessment end to end.

usage: python scripts/ci/smoke_api.py [PORT]         a local container or server (default 8000)
       python scripts/ci/smoke_api.py https://HOST   the deployed API

It talks to this machine (127.0.0.1) or, over HTTPS, to a Container Apps host or the project's
own domain; nothing else. A deployed API may be scaled to zero, so the first health check waits
for it to start and reports how long that took (the cold start).

Checks /health, submits the Cayman Synth Capital demo scenario, follows its progress stream until
the final status, then fetches the report and checks its tier and where each result came from.
Standard library only, so it runs against the container without installing anything.
"""

from __future__ import annotations

import json
import re
import sys
import time
from urllib.request import Request, urlopen

REQUEST = {"entity_name": "Cayman Synth Capital", "entity_type": "corporate", "jurisdiction": "KY"}
AGENTS = ("identity", "screening", "corporate", "transaction", "compliance")
EXPECTED_SOURCES = {**dict.fromkeys(AGENTS[:4], "demo_profile"), "compliance": "computed"}
DEPLOYED = re.compile(
    r"https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:azurecontainerapps\.io|arjunganesh\.dev)"
)


def call(base: str, path: str, body: dict | None = None, timeout: float = 30) -> bytes:
    url = base + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    request = Request(url, data=data, headers=headers)  # noqa: S310 - base checked by target()
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - base checked by target()
        return response.read()


def wait_for_health(base: str, seconds: float = 60) -> float:
    """Seconds until /health answered ok."""
    start = time.monotonic()
    deadline = start + seconds
    while True:
        try:
            health = json.loads(call(base, "/health", timeout=10))
        except (OSError, ValueError) as exc:
            health = exc
        if health == {"status": "ok"}:
            return time.monotonic() - start
        if time.monotonic() > deadline:
            raise TimeoutError(f"/health did not report ok within {seconds:g} s: {health!r}")
        time.sleep(1)


def stream_events(base: str, report_id: str) -> list[dict]:
    text = call(base, f"/api/v1/kyc/stream/{report_id}", timeout=120).decode()
    events = []
    for block in text.replace("\r\n", "\n").strip().split("\n\n"):
        data = [line[6:] for line in block.splitlines() if line.startswith("data: ")]
        if data:
            events.append(json.loads(data[0]))
    return events


def smoke(base: str, wait: float = 60) -> list[str]:
    print(f"/health answered after {wait_for_health(base, wait):.1f} s.")
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
    if report.get("risk_summary", {}).get("overall_risk_tier") != "CRITICAL":
        problems.append(f"tier: {report.get('risk_summary')}")
    if report.get("audit_trace", {}).get("agent_sources") != EXPECTED_SOURCES:
        problems.append(f"sources: {report.get('audit_trace', {}).get('agent_sources')}")
    if not report.get("regulatory_triggers"):
        problems.append("no regulatory triggers: the regulations search found nothing")
    return problems


def target(arg: str) -> str:
    """The API's base URL: a local port, or a deployed API's HTTPS origin."""
    if arg.startswith("https://"):
        if not DEPLOYED.fullmatch(arg.rstrip("/")):
            raise ValueError(f"Not a Container Apps host or the project's domain: {arg}")
        return arg.rstrip("/")
    port = int(arg)
    if not 0 < port < 65536:
        raise ValueError(f"Not a TCP port: {port}")
    return f"http://127.0.0.1:{port}"


def main(argv: list[str]) -> int:
    base = target(argv[1] if len(argv) > 1 else "8000")
    # A deployed API scaled to zero first has to pull its image and start.
    problems = smoke(base, wait=240 if base.startswith("https://") else 60)
    print("\n".join(problems) if problems else f"Smoke assessment passed against {base}.")
    return int(bool(problems))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
