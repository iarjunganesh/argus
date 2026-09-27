"""The orchestrator workflow: fan-out, fan-in, demo scenarios, degradation and progress events."""

import pytest

from argus.agents.orchestrator import agent as orchestrator

REQUEST = {"entity_name": "TestCo", "entity_type": "corporate", "jurisdiction": "NL"}


@pytest.fixture
def fake_agents(monkeypatch):
    """Replace every agent with one that records its call and answers `{"foo": name}`."""
    calls: dict[str, dict] = {}

    def fake(name):
        async def assess(request, task_id):
            calls[name] = request
            return {
                "agent": name,
                "status": "completed",
                "source": "computed",
                "fallbacks": [],
                "result": {"foo": name},
            }

        return assess

    for name, module in orchestrator._MODULES.items():
        monkeypatch.setattr(module, "assess", fake(name))
    return calls


async def test_the_four_agents_fan_in_to_compliance(fake_agents):
    report = await orchestrator.run_kyc_assessment(REQUEST)

    assert set(fake_agents) == set(orchestrator.AGENTS)
    for name in orchestrator.PARALLEL_AGENTS:
        assert fake_agents[name] == REQUEST
    upstream = fake_agents["compliance"]["upstream_results"]
    assert {name: r["result"] for name, r in upstream.items()} == {
        name: {"foo": name} for name in orchestrator.PARALLEL_AGENTS
    }
    assert fake_agents["compliance"]["entity_name"] == "TestCo"
    assert report["entity"]["name"] == "TestCo"
    assert report["audit_trace"]["agents_invoked"] == list(orchestrator.AGENTS)
    assert set(report["audit_trace"]["agent_sources"].values()) == {"computed"}


async def test_an_agent_that_fails_is_unavailable_and_the_others_continue(fake_agents, monkeypatch):
    async def broken(request, task_id):
        raise RuntimeError("identity down")

    monkeypatch.setattr(orchestrator._MODULES["identity"], "assess", broken)

    report = await orchestrator.run_kyc_assessment(REQUEST)

    trace = report["audit_trace"]
    assert trace["identity_status"] == "error"
    assert trace["agent_sources"]["identity"] == "unavailable"
    assert trace["agent_sources"]["screening"] == "computed"
    upstream = fake_agents["compliance"]["upstream_results"]
    assert upstream["identity"]["result"] is None
    assert upstream["identity"]["error"] == "identity down"


async def test_a_demo_scenario_stands_in_for_the_parallel_agents(fake_agents):
    request = {"entity_name": "Jane Synthetic", "entity_type": "individual", "jurisdiction": "DE"}

    report = await orchestrator.run_kyc_assessment(request)

    assert set(fake_agents) == {"compliance"}  # the four parallel agents were not run
    upstream = fake_agents["compliance"]["upstream_results"]
    assert upstream["identity"]["result"]["identity_score"] == 96
    assert upstream["transaction"]["result"]["transaction_count"] == 8
    sources = report["audit_trace"]["agent_sources"]
    assert [sources[a] for a in orchestrator.AGENTS] == ["demo_profile"] * 4 + ["computed"]


async def test_a_demo_scenario_without_a_section_gives_that_agent_an_empty_result(
    fake_agents, monkeypatch
):
    from argus.utils import demo_profiles

    monkeypatch.setattr(
        demo_profiles, "get_demo_profile", lambda name, etype, j: {"identity": {"x": 1}}
    )

    await orchestrator.run_kyc_assessment(REQUEST)

    upstream = fake_agents["compliance"]["upstream_results"]
    assert upstream["identity"]["result"] == {"x": 1}
    assert upstream["corporate"]["result"] == {}


async def test_each_agent_reports_its_start_and_finish(fake_agents, monkeypatch):
    async def partly(request, task_id):
        return {
            "agent": "screening",
            "status": "completed",
            "source": "fallback",
            "fallbacks": ["sanctions_checker"],
            "result": {},
        }

    monkeypatch.setattr(orchestrator._MODULES["screening"], "assess", partly)
    events = []

    async def sink(event):
        events.append(event)

    await orchestrator.run_kyc_assessment(REQUEST, on_event=sink)

    for name in orchestrator.AGENTS:
        kinds = [e["type"] for e in events if e["agent"] == name]
        assert kinds == ["agent_started", "agent_completed"], name
    completed = {e["agent"]: e for e in events if e["type"] == "agent_completed"}
    assert completed["screening"]["source"] == "fallback"
    assert completed["screening"]["fallbacks"] == ["sanctions_checker"]
    assert completed["identity"] == {
        "type": "agent_completed",
        "agent": "identity",
        "at": completed["identity"]["at"],
        "status": "completed",
        "source": "computed",
        "fallbacks": [],
    }
    # Compliance starts only after all four parallel agents have finished.
    order = [(e["type"], e["agent"]) for e in events]
    compliance_start = order.index(("agent_started", "compliance"))
    finished_before = {a for kind, a in order[:compliance_start] if kind == "agent_completed"}
    assert finished_before == set(orchestrator.PARALLEL_AGENTS)


async def test_the_report_has_a_timeline_and_latency(fake_agents):
    report = await orchestrator.run_kyc_assessment(REQUEST)

    steps = [entry["step"] for entry in report["timeline"]]
    assert steps == [
        "Request received",
        "Identity Agent",
        "Screening Agent",
        "Corporate Agent",
        "Transaction Agent",
        "Parallel agents complete",
        "Compliance & Risk Agent",
        "Final report generated",
    ]
    assert report["total_latency_seconds"] >= 0


def test_the_workflow_graph_is_dispatch_then_four_agents_then_compliance():
    workflow = orchestrator.build_workflow()

    assert set(workflow.executors) == {"dispatch", *orchestrator.AGENTS}


async def test_synthesise_report_handles_missing_and_present_fields():
    # compliance with result keys
    comp = {
        "status": "ok",
        "result": {
            "risk_summary": {"tier": "HIGH"},
            "explanation": "Found risks",
            "explanation_source": "model",
            "retrieval_queries": 2,
        },
        "source": "computed",
    }
    identity = {"status": "ok", "source": "fallback", "fallbacks": ["ocr_processor[0]"]}
    screening = {"status": "ok", "source": "demo_profile", "result": {"retrieval_queries": 1}}
    corporate = {"status": "ok"}
    transaction = {"status": "ok"}

    rpt = await orchestrator.synthesise_report(
        "tid", {"entity_name": "Acme"}, identity, screening, corporate, transaction, comp
    )
    assert rpt["report_id"].startswith("argus-rpt-")
    assert rpt["entity"]["name"] == "Acme"
    assert rpt["risk_summary"]["tier"] == "HIGH"
    assert rpt["explanation_source"] == "model"
    trace = rpt["audit_trace"]
    assert trace["retrieval_queries"] == 3
    assert trace["data_backend"] == "local"
    assert trace["agent_sources"]["identity"] == "fallback"
    assert trace["agent_sources"]["screening"] == "demo_profile"
    assert trace["fallbacks"] == {"identity": ["ocr_processor[0]"]}
