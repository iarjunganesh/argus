"""API: submit, poll, fetch, stream, health, and the background assessment."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

import argus.agents.orchestrator.agent as orchestrator
from argus.api import main

REQUEST = {"entity_name": "Acme", "entity_type": "corporate", "jurisdiction": "NL"}


@pytest.fixture
def client():
    return TestClient(main.app)  # conftest gives each test a fresh in-memory report store


def test_submitted_assessment_can_be_polled_and_fetched(client, monkeypatch):
    received = []

    async def assessment(request, on_event):
        received.append(request)
        return {"risk_summary": {"overall_risk_tier": "LOW"}}

    monkeypatch.setattr(orchestrator, "run_kyc_assessment", assessment)

    submitted = client.post("/api/v1/kyc/assess", json=REQUEST).json()
    report_id = submitted["report_id"]

    assert submitted["status"] == "processing"
    assert received[0]["entity_name"] == "Acme"
    assert client.get(f"/api/v1/kyc/status/{report_id}").json()["status"] == "completed"
    report = client.get(f"/api/v1/kyc/report/{report_id}").json()
    assert report == {"risk_summary": {"overall_risk_tier": "LOW"}, "report_id": report_id}


def test_failed_assessment_is_reported_as_error(client, monkeypatch):
    async def assessment(request, on_event):
        raise RuntimeError("orchestrator down")

    monkeypatch.setattr(orchestrator, "run_kyc_assessment", assessment)

    report_id = client.post("/api/v1/kyc/assess", json=REQUEST).json()["report_id"]

    assert client.get(f"/api/v1/kyc/status/{report_id}").json()["status"] == "error"
    report = client.get(f"/api/v1/kyc/report/{report_id}").json()
    assert report["error"] == "orchestrator down"


def test_unknown_report_is_404_with_status(client):
    response = client.get("/api/v1/kyc/report/nope")

    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found. Status: not_found"
    assert client.get("/api/v1/kyc/status/nope").json()["status"] == "not_found"


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_api_root():
    from argus.api.main import app

    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "ARGUS"


def test_reports_are_written_through_the_report_store(client, use_plane, monkeypatch):
    from argus.data_plane.local import MemoryReportStore

    store = MemoryReportStore()
    use_plane(reports=store)

    async def assessment(request, on_event):
        return {"risk_summary": {}}

    monkeypatch.setattr(orchestrator, "run_kyc_assessment", assessment)
    report_id = client.post("/api/v1/kyc/assess", json=REQUEST).json()["report_id"]

    assert asyncio.run(store.status(report_id)) == "completed"
    assert asyncio.run(store.report(report_id))["report_id"] == report_id


def test_cors_origins_come_from_settings(monkeypatch):
    monkeypatch.setenv("ARGUS_CORS_ORIGINS", " https://ui.example , ,http://localhost:3000")

    assert main.cors_origins() == ["https://ui.example", "http://localhost:3000"]


def test_no_browser_origin_is_allowed_by_default(client):
    response = client.get("/", headers={"Origin": "https://elsewhere.example"})

    assert main.cors_origins() == []
    assert "access-control-allow-origin" not in response.headers


# ── demo-only mode (ARGUS_DEMO_ONLY) ─────────────────────────────────────────

CAYMAN = {"entity_name": "Cayman Synth Capital", "entity_type": "corporate", "jurisdiction": "KY"}


@pytest.fixture
def demo_only(monkeypatch):
    monkeypatch.setenv("ARGUS_DEMO_ONLY", "true")

    async def assessment(request, on_event):
        return {"risk_summary": {}}

    monkeypatch.setattr(orchestrator, "run_kyc_assessment", assessment)


@pytest.mark.parametrize(
    "request_body",
    [
        REQUEST,
        {**CAYMAN, "jurisdiction": "DE"},
        {**CAYMAN, "aliases": ["Someone Real"]},
        {**CAYMAN, "date_of_birth": "1970-01-01"},
        {**CAYMAN, "registration_number": "123"},
    ],
)
def test_demo_only_refuses_anything_but_a_synthetic_demo_case(client, demo_only, request_body):
    response = client.post("/api/v1/kyc/assess", json=request_body)

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "This deployment runs only the synthetic demo cases: Synthetic Holdings B.V. (corporate, "
        "NL); Jane Synthetic (individual, DE); Cayman Synth Capital (corporate, KY)"
    )


def test_demo_only_runs_the_synthetic_demo_cases(client, demo_only):
    body = {**CAYMAN, "entity_name": "  cayman synth CAPITAL ", "jurisdiction": "ky"}

    report_id = client.post("/api/v1/kyc/assess", json=body).json()["report_id"]

    assert client.get(f"/api/v1/kyc/status/{report_id}").json()["status"] == "completed"


@pytest.mark.parametrize(
    ("value", "on"), [("", False), ("false", False), ("TRUE", True), ("1", True)]
)
def test_demo_only_is_off_unless_set(monkeypatch, value, on):
    monkeypatch.setenv("ARGUS_DEMO_ONLY", value)

    assert main.demo_only() is on


def test_submitted_names_stay_out_of_the_logs(client, two_agents, caplog):
    caplog.set_level("INFO")

    client.post("/api/v1/kyc/assess", json=REQUEST)

    logged = [str(vars(record)) for record in caplog.records]
    assert logged and not any("Acme" in line for line in logged)


# ── progress stream (server-sent events) ─────────────────────────────────────


def _parse_sse(text: str) -> list[dict]:
    """Split an event stream into its events: `{"event": ..., "id": ..., "data": ...}`."""
    events = []
    for block in text.strip().replace("\r\n", "\n").split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append({**fields, "data": json.loads(fields["data"])})
    return events


@pytest.fixture
def two_agents(monkeypatch):
    """An assessment whose workflow reports one agent starting and finishing."""

    async def assessment(request, on_event):
        await on_event({"type": "agent_started", "agent": "identity"})
        await on_event({"type": "agent_completed", "agent": "identity", "source": "fallback"})
        return {"risk_summary": {}}

    monkeypatch.setattr(orchestrator, "run_kyc_assessment", assessment)


def test_the_stream_replays_each_agent_event_then_the_final_status(client, two_agents):
    report_id = client.post("/api/v1/kyc/assess", json=REQUEST).json()["report_id"]

    response = client.get(f"/api/v1/kyc/stream/{report_id}")

    assert response.headers["content-type"].startswith("text/event-stream")
    assert _parse_sse(response.text) == [
        {
            "event": "agent_started",
            "id": "0",
            "data": {"type": "agent_started", "agent": "identity"},
        },
        {
            "event": "agent_completed",
            "id": "1",
            "data": {"type": "agent_completed", "agent": "identity", "source": "fallback"},
        },
        {
            "event": "status",
            "data": {"type": "status", "report_id": report_id, "status": "completed"},
        },
    ]


def test_a_reconnecting_client_resumes_after_its_last_event(client, two_agents):
    report_id = client.post("/api/v1/kyc/assess", json=REQUEST).json()["report_id"]

    resumed = client.get(f"/api/v1/kyc/stream/{report_id}", headers={"Last-Event-ID": "0"})
    garbled = client.get(f"/api/v1/kyc/stream/{report_id}", headers={"Last-Event-ID": "x"})

    assert [e["event"] for e in _parse_sse(resumed.text)] == ["agent_completed", "status"]
    assert len(_parse_sse(garbled.text)) == 3  # an unusable ID replays everything


def test_the_stream_of_an_unknown_report_is_404(client):
    response = client.get("/api/v1/kyc/stream/nope")

    assert response.status_code == 404


async def test_the_stream_follows_an_assessment_that_is_still_running(monkeypatch):
    from argus.data_plane import get_data_plane

    monkeypatch.setattr(main, "STREAM_POLL_SECONDS", 0.001)
    reports = get_data_plane().reports
    await reports.save_status("r1", "processing")

    async def run():
        await asyncio.sleep(0.01)
        await reports.append_event("r1", {"type": "agent_started"})
        await asyncio.sleep(0.01)
        await reports.save_status("r1", "completed")

    task = asyncio.create_task(run())
    events = [e async for e in main.progress_events("r1")]
    await task

    assert [(e.event, e.id) for e in events] == [("agent_started", "0"), ("status", None)]
    assert events[-1].data["status"] == "completed"


async def test_the_stream_closes_at_its_time_limit_with_the_current_status(monkeypatch):
    from argus.data_plane import get_data_plane

    monkeypatch.setattr(main, "STREAM_MAX_SECONDS", 0)
    await get_data_plane().reports.save_status("r1", "processing")

    events = [e async for e in main.progress_events("r1")]

    assert [(e.event, e.data["status"]) for e in events] == [("status", "processing")]
