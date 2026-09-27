"""API: submit, poll, fetch, health, and the background assessment."""

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

    async def assessment(request):
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
    async def assessment(request):
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

    async def assessment(request):
        return {"risk_summary": {}}

    monkeypatch.setattr(orchestrator, "run_kyc_assessment", assessment)
    report_id = client.post("/api/v1/kyc/assess", json=REQUEST).json()["report_id"]

    assert store._status[report_id] == "completed"
    assert store._reports[report_id]["report_id"] == report_id


def test_cors_origins_come_from_settings(monkeypatch):
    monkeypatch.setenv("ARGUS_CORS_ORIGINS", " https://ui.example , ,http://localhost:3000")

    assert main.cors_origins() == ["https://ui.example", "http://localhost:3000"]


def test_no_browser_origin_is_allowed_by_default(client):
    response = client.get("/", headers={"Origin": "https://elsewhere.example"})

    assert main.cors_origins() == []
    assert "access-control-allow-origin" not in response.headers
