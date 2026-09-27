"""The API's public contract: what a client (the Gradio UI today, the web UI next) relies on.

`tests/fixtures/openapi.json` is the reviewed OpenAPI document. A change to a path, method,
parameter or schema fails here until the fixture is regenerated on purpose:

    UPDATE_API_CONTRACT=1 uv run pytest tests/test_api_contract.py

The report and the progress events are plain JSON objects, so their fields are pinned below.
"""

import json
import os
from pathlib import Path

import pytest

from argus.agents.orchestrator import agent as orchestrator
from argus.api import main

CONTRACT = Path(__file__).parent / "fixtures" / "openapi.json"

REPORT_FIELDS = {
    "report_id",
    "generated_at",
    "explanation",
    "explanation_source",
    "entity",
    "risk_summary",
    "dimension_scores",
    "key_findings",
    "regulatory_triggers",
    "recommended_actions",
    "audit_trace",
    "timeline",
    "total_latency_seconds",
}
RISK_SUMMARY_FIELDS = {
    "overall_risk_tier",
    "overall_risk_score",
    "tier_basis",
    "sanctions_screening",
    "edd_required",
    "decision_recommendation",
}
AUDIT_TRACE_FIELDS = {
    "task_id",
    "agents_invoked",
    "retrieval_queries",
    "data_backend",
    "agent_sources",
    "fallbacks",
    "identity_status",
    "screening_status",
    "corporate_status",
    "transaction_status",
    "compliance_status",
}


def test_the_openapi_document_matches_the_reviewed_contract():
    current = main.app.openapi()
    if os.getenv("UPDATE_API_CONTRACT"):
        CONTRACT.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert current == json.loads(CONTRACT.read_text(encoding="utf-8")), (
        "The API changed. If that is intended, regenerate tests/fixtures/openapi.json "
        "(see this module's docstring) and review the diff."
    )


def test_the_endpoints_a_client_uses():
    paths = main.app.openapi()["paths"]

    assert {path: sorted(ops) for path, ops in paths.items()} == {
        "/": ["get"],
        "/health": ["get"],
        "/api/v1/kyc/assess": ["post"],
        "/api/v1/kyc/report/{report_id}": ["get"],
        "/api/v1/kyc/status/{report_id}": ["get"],
        "/api/v1/kyc/stream/{report_id}": ["get"],
    }
    stream = paths["/api/v1/kyc/stream/{report_id}"]["get"]
    assert "text/event-stream" in stream["responses"]["200"]["content"]


@pytest.mark.parametrize("entity_type", ["corporate", "individual"])
async def test_a_computed_report_has_every_contract_field(entity_type):
    events = []

    async def sink(event):
        events.append(event)

    request = {"entity_name": "Ada Synthetic", "entity_type": entity_type, "jurisdiction": "NL"}
    report = await orchestrator.run_kyc_assessment(request, on_event=sink)

    assert set(report) == REPORT_FIELDS
    assert set(report["risk_summary"]) == RISK_SUMMARY_FIELDS
    assert set(report["audit_trace"]) == AUDIT_TRACE_FIELDS
    assert set(report["entity"]) == {"name", "type", "jurisdiction"}
    assert all(set(t) == {"rule", "citation"} for t in report["regulatory_triggers"])
    assert all(set(e) == {"step", "time"} for e in report["timeline"])
    assert {e["type"] for e in events} == {"agent_started", "agent_completed"}
    assert all(set(e) == {"type", "agent", "at"} for e in events if e["type"] == "agent_started")
    assert all(
        set(e) == {"type", "agent", "at", "status", "source", "fallbacks"}
        for e in events
        if e["type"] == "agent_completed"
    )
