"""API gateway: submit, poll, fetch, admin endpoints, and the background assessment."""

import httpx
import pytest
from fastapi.testclient import TestClient

import agents.orchestrator.agent as orchestrator
from api import main

REQUEST = {"entity_name": "Acme", "entity_type": "corporate", "jurisdiction": "NL"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "_reports", {})
    monkeypatch.setattr(main, "_status", {})
    return TestClient(main.app)


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


def test_agent_registry_honours_url_overrides(client, monkeypatch):
    monkeypatch.setenv("SCREENING_AGENT_URL", "http://screening.internal")

    agents = {a["name"]: a["endpoint"] for a in client.get("/api/v1/admin/agents").json()["agents"]}

    assert agents["identity"] == "http://localhost:8001"
    assert agents["screening"] == "http://screening.internal"


def test_aggregated_health_reports_each_outcome(client, monkeypatch):
    def fake_get(url, timeout):
        request = httpx.Request("GET", url)
        if ":8001" in url:
            return httpx.Response(200, json={"service": "identity"}, request=request)
        if ":8002" in url:
            return httpx.Response(503, request=request)
        raise httpx.ConnectError("refused", request=request)

    monkeypatch.setattr(httpx, "get", fake_get)

    health = client.get("/api/v1/admin/health").json()["aggregated"]

    assert health["identity"] == {"status": "ok", "info": {"service": "identity"}}
    assert health["screening"] == {"status": "error", "code": 503}
    assert health["corporate"]["status"] == "unreachable"
