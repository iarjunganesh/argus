"""The six documented demo scenarios keep their recorded outcomes.

`tests/fixtures/demo_scenarios.json` was recorded before the data-plane refactor. A change that
moves a tier, a score, a finding or a recommended action shows up here. Regulatory triggers are
checked for citations only: they come from knowledge-base retrieval, which the refactor made real.
"""

import json
from pathlib import Path

import pytest

import argus.agents.orchestrator.agent as orchestrator

SCENARIOS = json.loads(
    (Path(__file__).parent / "fixtures" / "demo_scenarios.json").read_text(encoding="utf-8")
)
AGENTS = ("identity", "screening", "corporate", "transaction", "compliance")


async def _in_process(agent_name: str, payload: dict, task_id: str) -> dict:
    """Call an agent's handler directly instead of over HTTP."""
    module = __import__(f"argus.agents.{agent_name}.agent", fromlist=["invoke"])
    message = module.A2AMessage(
        a2a_version="1.0",
        source_agent="test",
        target_agent=agent_name,
        task_id=task_id,
        payload=payload,
    )
    return await module.invoke(message)


@pytest.mark.parametrize(
    "scenario", SCENARIOS, ids=[s["request"]["entity_name"] for s in SCENARIOS]
)
async def test_demo_scenario_outcome_is_unchanged(monkeypatch, scenario):
    monkeypatch.setattr(orchestrator, "call_agent", _in_process)

    report = await orchestrator.run_kyc_assessment(scenario["request"])

    for key in ("risk_summary", "dimension_scores", "key_findings", "recommended_actions"):
        assert report[key] == scenario[key], key
    assert report["regulatory_triggers"]
    assert all(t["citation"]["document"] for t in report["regulatory_triggers"])
    sources = report["audit_trace"]["agent_sources"]
    assert [sources[a] for a in AGENTS] == ["demo_profile"] * 4 + ["computed"]
    assert report["explanation_source"] == "fallback"  # no model is configured in tests
