"""tests/test_agents.py — Integration tests for agent endpoints using mock data."""
from fastapi.testclient import TestClient

SAMPLE_A2A = {
    "a2a_version": "1.0",
    "source_agent": "argus-orchestrator-v1",
    "target_agent": "argus-identity-agent-v1",
    "task_id":      "test-task-001",
    "payload": {
        "entity_name":   "Synthetic Entity Ltd.",
        "entity_type":   "corporate",
        "jurisdiction":  "NL",
        "aliases":       ["SE Ltd"],
    },
}

def test_identity_agent_health():
    from agents.identity.agent import app
    client = TestClient(app)
    resp = client.get("/docs")
    assert resp.status_code == 200

def test_screening_agent_invoke():
    from agents.screening.agent import app
    client = TestClient(app)
    resp = client.post("/a2a/invoke", json={**SAMPLE_A2A, "target_agent": "argus-screening-agent-v1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "screening"
    assert data["status"] == "completed"
    assert "screening_risk_score" in data["result"]


def test_public_demo_profile_is_available():
    from utils.demo_profiles import get_demo_profile

    profile = get_demo_profile("Wirecard AG", "corporate", "DE")
    assert profile is not None
    assert profile["screening"]["adverse_media_hit"] is True
    assert profile["screening"]["findings"][0]["foundry_iq_citation"]["document"] == "wirecard_public_enforcement_summary.json"


def test_demo_profile_aliases_resolve_to_canonical_profiles():
    from utils.demo_profiles import get_demo_profile

    wirecard = get_demo_profile("Wirecard", "corporate", "DE")
    cayman = get_demo_profile("Cayman Holdings", "corporate", "US")
    synthetic = get_demo_profile("Synthetic Holdings", "corporate", "US")
    jane = get_demo_profile("Jane Doe", "individual", "US")

    assert wirecard is not None and wirecard["screening"]["adverse_media_hit"] is True
    assert cayman is not None and cayman["screening"]["sanctions_hit"] is True
    assert synthetic is not None and synthetic["screening"]["pep_hit"] is True
    assert jane is not None and jane["screening"]["screening_risk_score"] == 5

def test_corporate_agent_skips_individual():
    from agents.corporate.agent import app
    client = TestClient(app)
    payload = {**SAMPLE_A2A, "payload": {**SAMPLE_A2A["payload"], "entity_type": "individual"}}
    resp = client.post("/a2a/invoke", json=payload)
    assert resp.status_code == 200
    assert resp.json()["result"].get("skipped") is True

def test_transaction_agent_invoke():
    from agents.transaction.agent import app
    client = TestClient(app)
    resp = client.post("/a2a/invoke", json={**SAMPLE_A2A, "target_agent": "argus-transaction-agent-v1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "transaction"
    assert "transaction_risk_score" in data["result"]

def test_api_root():
    from api.main import app
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "ARGUS"


def test_compliance_agent_handles_none_upstream_results():
    from agents.compliance.agent import app

    client = TestClient(app)
    payload = {
        "a2a_version": "1.0",
        "source_agent": "argus-orchestrator-v1",
        "target_agent": "argus-compliance-agent-v1",
        "task_id": "test-task-none-upstream",
        "payload": {
            "entity_name": "Synthetic Entity Ltd.",
            "entity_type": "corporate",
            "jurisdiction": "KY",
            "upstream_results": {
                "identity": {"status": "error", "result": None},
                "screening": {"status": "error", "result": None},
                "corporate": {"status": "completed", "result": {}},
                "transaction": {"status": "completed", "result": {}},
            },
        },
    }

    resp = client.post("/a2a/invoke", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "risk_summary" in data["result"]
    assert "explanation" in data["result"]
