"""Orchestrator transport: the A2A envelope sent to each sub-agent."""

import json

import httpx

from argus.agents.orchestrator import agent as orchestrator


async def test_call_agent_posts_envelope_and_returns_json(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"agent": "identity", "status": "completed"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )

    result = await orchestrator.call_agent("identity", {"entity_name": "X"}, "task-1")

    assert result == {"agent": "identity", "status": "completed"}
    assert str(seen[0].url) == f"{orchestrator.AGENT_URLS['identity']}/a2a/invoke"
    body = json.loads(seen[0].content)
    assert body["target_agent"] == "argus-identity-agent-v1"
    assert body["task_id"] == "task-1"
    assert body["payload"] == {"entity_name": "X"}


async def test_synthesise_report_handles_missing_and_present_fields():
    # compliance with result keys
    comp = {
        "status": "ok",
        "result": {
            "risk_summary": {"tier": "HIGH"},
            "explanation": "Found risks",
            "foundry_iq_queries": 2,
        },
    }
    identity = {"status": "ok"}
    screening = {"status": "ok", "result": {"foundry_iq_queries": 1}}
    corporate = {"status": "ok"}
    transaction = {"status": "ok"}

    rpt = await orchestrator.synthesise_report(
        "tid", {"entity_name": "Acme"}, identity, screening, corporate, transaction, comp
    )
    assert rpt["report_id"].startswith("argus-rpt-")
    assert rpt["entity"]["name"] == "Acme"
    assert rpt["risk_summary"]["tier"] == "HIGH"
    # foundry_iq_queries aggregated
    assert rpt["audit_trace"]["foundry_iq_queries"] == 3


async def test_run_kyc_assessment_with_mocked_call_agent(monkeypatch):
    # Patch call_agent to return simple structured results for each agent
    async def fake_call(agent_name, payload, task_id):
        return {"agent": agent_name, "status": "ok", "result": {"foo": agent_name}}

    monkeypatch.setattr(orchestrator, "call_agent", fake_call)

    kyc = {"entity_name": "TestCo", "entity_type": "company", "jurisdiction": "NL"}
    report = await orchestrator.run_kyc_assessment(kyc)
    assert report["entity"]["name"] == "TestCo"
    assert "audit_trace" in report
    assert report["audit_trace"]["agents_invoked"] == [
        "identity",
        "screening",
        "corporate",
        "transaction",
        "compliance",
    ]


async def test_run_kyc_assessment_uses_demo_profile_shortcut(monkeypatch):
    import argus.utils.demo_profiles as demo_profiles

    calls = []

    async def fake_call(agent_name, payload, task_id):
        calls.append(agent_name)
        return {"agent": agent_name, "status": "ok", "result": {"foo": agent_name}}

    monkeypatch.setattr(orchestrator, "call_agent", fake_call)

    # Force deterministic shortcut branch.
    monkeypatch.setattr(
        demo_profiles,
        "get_demo_profile",
        lambda name, etype, j: {
            "identity": {"identity_score": 95},
            "screening": {"screening_risk_score": 5},
            "corporate": {"corporate_score": 5},
            "transaction": {"transaction_risk_score": 5},
        },
    )

    kyc = {"entity_name": "DemoCo", "entity_type": "corporate", "jurisdiction": "US"}
    report = await orchestrator.run_kyc_assessment(kyc)

    assert report["entity"]["name"] == "DemoCo"
    assert calls == ["compliance"]


async def test_call_agent_http_error(monkeypatch):
    import httpx

    from argus.agents.orchestrator import agent as orch

    async def raise_http(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    # Monkeypatch httpx.AsyncClient.post
    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeAsyncClient())
    result = await orch.call_agent("identity", {"entity_name": "X"}, "task-err-001")
    assert result["status"] == "error"
    assert result["agent"] == "identity"
