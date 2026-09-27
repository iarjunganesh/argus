"""The six documented demo scenarios keep their recorded outcomes.

`tests/fixtures/demo_scenarios.json` was recorded before the data-plane refactor, then re-recorded
once when a potential sanctions match began to hold the case: only Cayman Synth Capital changed
(HIGH to CRITICAL, with the hold's finding and actions; no score moved). Re-recorded again when a
PEP match began to require enhanced due diligence: the two PEP scenarios gain `edd_required` and a
monitoring action, and Synthetic Holdings B.V. gets the EDD recommendation; no tier or score moved.
Unchanged when the five agent services became one in-process Agent Framework workflow.
A change that moves a tier, a score, a finding or a recommended action shows up here. Regulatory
triggers are checked for citations only: they come from knowledge-base retrieval, which the
refactor made real.
"""

import json
from pathlib import Path

import pytest

import argus.agents.orchestrator.agent as orchestrator

SCENARIOS = json.loads(
    (Path(__file__).parent / "fixtures" / "demo_scenarios.json").read_text(encoding="utf-8")
)
AGENTS = ("identity", "screening", "corporate", "transaction", "compliance")


@pytest.mark.parametrize(
    "scenario", SCENARIOS, ids=[s["request"]["entity_name"] for s in SCENARIOS]
)
async def test_demo_scenario_outcome_is_unchanged(scenario):
    report = await orchestrator.run_kyc_assessment(scenario["request"])

    for key in ("risk_summary", "dimension_scores", "key_findings", "recommended_actions"):
        assert report[key] == scenario[key], key
    assert report["regulatory_triggers"]
    assert all(t["citation"]["document"] for t in report["regulatory_triggers"])
    sources = report["audit_trace"]["agent_sources"]
    assert [sources[a] for a in AGENTS] == ["demo_profile"] * 4 + ["computed"]
    assert report["explanation_source"] == "fallback"  # no model is configured in tests
