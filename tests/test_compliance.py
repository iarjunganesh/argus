"""Compliance agent and its tools: tiering, findings, actions, explanations, regulations."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

import argus.agents.compliance.agent as comp
import argus.agents.compliance.tools.explain_decision as ed
import argus.agents.compliance.tools.regulations_rag as rr
from argus.agents.compliance.tools.gap_analyzer import gap_analyzer
from argus.agents.compliance.tools.risk_scorer import risk_scorer


def _msg(upstream: dict) -> comp.A2AMessage:
    return comp.A2AMessage(
        a2a_version="1.0",
        source_agent="test",
        target_agent="compliance",
        task_id="t-comp",
        payload={
            "entity_name": "Acme",
            "entity_type": "corporate",
            "jurisdiction": "NL",
            "upstream_results": {k: {"result": v} for k, v in upstream.items()},
        },
    )


class FakeLLM:
    """Stands in for AsyncOpenAI: records the prompt and returns fixed content."""

    def model(self):
        """This client as the configured chat model, for patching `get_chat_model`."""
        from argus.models import ChatModel

        return lambda: ChatModel("test", "test-model", self)

    def __init__(self, content: str | None = None, error: Exception | None = None):
        self.content = content
        self.error = error
        self.prompts: list[str] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.prompts.append(kwargs["messages"][0]["content"])
        if self.error:
            raise self.error
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


# ── agent ─────────────────────────────────────────────────────────────────────


async def test_every_risk_indicator_reaches_findings_and_actions():
    upstream = {
        "identity": {"identity_score": 20},
        "screening": {
            "pep_hit": True,
            "sanctions_hit": True,
            "adverse_media_hit": True,
            "screening_risk_score": 100,
            "findings": [{"type": "pep", "match": "Minister X"}, {"type": "sanctions"}],
        },
        "corporate": {"risk_flags": ["Offshore node: KY"], "corporate_score": 20},
        "transaction": {"structuring_flag": True, "transaction_risk_score": 100},
    }

    result = (await comp.invoke(_msg(upstream)))["result"]

    assert result["risk_summary"]["overall_risk_tier"] == "CRITICAL"
    assert result["risk_summary"]["decision_recommendation"].startswith("Hold:")
    assert result["key_findings"] == [
        "PEP identified: Minister X",
        "Adverse media coverage found — review required",
        "⚠️ Potential sanctions match: a person must confirm or clear it",
        "Offshore node: KY",
        "Transaction structuring pattern detected",
    ]
    actions = result["recommended_actions"]
    assert any(a.startswith("If confirmed: freeze funds without delay") for a in actions)
    assert "Obtain beneficial owner register for all offshore entities" in actions
    assert "Consider filing Suspicious Activity Report (SAR)" in actions
    assert "Conduct in-person verification or enhanced video KYC" in actions


async def test_medium_tier_and_non_pep_findings_are_skipped():
    upstream = {
        "identity": {"identity_score": 80},
        "screening": {
            "pep_hit": True,
            "screening_risk_score": 60,
            "findings": [{"type": "adverse_media", "match": "ignored"}, {"type": "pep"}],
        },
        "corporate": {"corporate_score": 80},
        "transaction": {},
    }

    result = (await comp.invoke(_msg(upstream)))["result"]

    assert result["risk_summary"]["overall_risk_tier"] == "MEDIUM"
    assert result["key_findings"] == ["PEP identified: "]


async def test_clean_entity_is_low_risk_with_default_action():
    result = (await comp.invoke(_msg({"screening": {"sanctions_hit": False}})))["result"]

    assert result["risk_summary"]["overall_risk_tier"] == "LOW"
    assert result["risk_summary"]["sanctions_screening"] == "no_match"
    assert result["risk_summary"]["decision_recommendation"].startswith("Standard onboarding")
    assert result["key_findings"] == [
        "No high-risk indicators found across all screening dimensions"
    ]
    assert result["recommended_actions"] == ["Continue standard periodic review cycle"]


async def test_a_sanctions_match_alone_holds_the_case_whatever_the_score():
    screening = {"sanctions_hit": True, "screening_risk_score": 60, "findings": []}

    result = (await comp.invoke(_msg({"screening": screening})))["result"]

    summary = result["risk_summary"]
    assert summary["overall_risk_score"] < 35  # the weighted score alone would be LOW
    assert summary["overall_risk_tier"] == "CRITICAL"
    assert summary["tier_basis"] == "sanctions_match"
    assert summary["sanctions_screening"] == "potential_match"
    assert summary["decision_recommendation"].startswith("Hold:")
    assert result["explanation"].startswith("This case is held at CRITICAL")
    assert (
        "FATF Rec.6 — Targeted financial sanctions screening mandatory"
        in (result["compliance_gaps"])
    )


async def test_a_case_whose_sanctions_screening_did_not_run_is_incomplete():
    fell_back = {"result": {"sanctions_hit": False}, "fallbacks": ["sanctions_checker"]}
    for screening in ({}, {"status": "error", "result": None}, fell_back):
        message = _msg({})
        message.payload["upstream_results"]["screening"] = screening

        result = (await comp.invoke(message))["result"]

        summary = result["risk_summary"]
        assert summary["sanctions_screening"] == "not_run"
        assert summary["tier_basis"] == "score"
        assert summary["decision_recommendation"].startswith("Incomplete:")
        assert "⚠️ Sanctions screening did not run" in result["key_findings"]
        assert (
            "Run sanctions screening before any onboarding decision"
            in (result["recommended_actions"])
        )


def test_every_score_band_maps_to_its_tier():
    from argus.agents.compliance.tools.risk_scorer import score_tier

    assert [score_tier(s) for s in (-1, 0, 34.9, 35, 55, 75, 100)] == [
        "LOW",
        "LOW",
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
        "CRITICAL",
    ]


def test_unknown_tier_recommendation():
    assert comp._recommendation("UNKNOWN") == "Review required."


def test_health():
    assert TestClient(comp.app).get("/health").json()["service"] == "compliance"


# ── risk scorer and gap analyzer ──────────────────────────────────────────────


def test_adverse_media_only_case_gets_boost():
    screening = {"adverse_media_hit": True, "screening_risk_score": 70}
    boosted = risk_scorer({}, screening, {}, {})
    plain = risk_scorer({}, {**screening, "pep_hit": True}, {}, {})

    # identity 4 + screening 21 + corporate 3 + regulatory, plus 12 only for the adverse-only
    # case; the score is rounded to one decimal.
    assert boosted["overall"] == 48.8  # 4 + 21 + 3 + 8.75 + 12
    assert plain["overall"] == 48.0  # 4 + 21 + 3 + 20, no boost
    assert boosted["dimensions"]["regulatory"]["tier"] == "MEDIUM"


def test_critical_score_adds_legal_hold():
    gaps = gap_analyzer([], {}, {"overall": 80})
    assert gaps[-1].startswith("Legal hold")


# ── explain_decision ──────────────────────────────────────────────────────────


async def test_explanation_comes_from_the_model(monkeypatch):
    llm = FakeLLM(content="  Rated HIGH because of PEP exposure.  ")
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    explanation = await ed.explain_decision(
        {"name": "Acme", "type": "corporate", "jurisdiction": "NL"},
        {"overall_risk_tier": "HIGH", "overall_risk_score": 60},
        {"identity": {"score": 10}},
        ["PEP identified"],
        [{"rule": "FATF Rec.12"}],
    )

    assert explanation == {"text": "Rated HIGH because of PEP exposure.", "source": "model"}
    assert "FATF Rec.12" in llm.prompts[0]
    assert "- Identity: 10/100" in llm.prompts[0]
    assert "Tier set by: the score band" in llm.prompts[0]
    assert "Sanctions screening: not reported" in llm.prompts[0]


async def test_the_model_is_told_when_a_sanctions_match_set_the_tier(monkeypatch):
    llm = FakeLLM(content="Held for a sanctions match.")
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    summary = {
        "overall_risk_tier": "CRITICAL",
        "overall_risk_score": 18,
        "tier_basis": "sanctions_match",
        "sanctions_screening": "potential_match",
    }
    await ed.explain_decision({}, summary, {}, [], [])

    assert "Tier set by: a potential sanctions match" in llm.prompts[0]
    assert "Sanctions screening: potential match, not yet confirmed" in llm.prompts[0]


async def test_explanation_falls_back_without_findings(monkeypatch):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(error=RuntimeError("down")).model())

    explanation = await ed.explain_decision({}, {"overall_risk_tier": "LOW"}, {}, [], [])

    assert explanation["source"] == "fallback"
    assert explanation["text"].startswith("This case was assessed as LOW risk based on")


async def test_explanation_without_a_configured_model_is_labelled_fallback():
    explanation = await ed.explain_decision({}, {"overall_risk_tier": "LOW"}, {}, ["X found"], [])

    assert explanation["source"] == "fallback"
    assert "primarily because x found" in explanation["text"]


async def test_an_empty_model_reply_is_not_passed_off_as_an_explanation(monkeypatch):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(content="   ").model())

    explanation = await ed.explain_decision({}, {"overall_risk_tier": "LOW"}, {}, [], [])

    assert explanation["source"] == "fallback"


async def test_plain_language_sections_are_parsed(monkeypatch):
    raw = (
        "Here is the letter.\n"
        "WHAT_HAPPENED: We reviewed your account.\n"
        "WHAT_WE_FOUND: Some details\n"
        "need checking.\n"
        "WHAT_HAPPENS_NEXT: We will write to you.\n"
        "CONTACT_INFO: Call us and quote REF-1."
    )
    llm = FakeLLM(content=raw)
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    result = await ed.explain_decision_plain_language(
        {"name": "Jane"}, {"overall_risk_tier": "MEDIUM"}, ["PEP identified"], "REF-1"
    )

    assert result == {
        "what_happened": "We reviewed your account.",
        "what_we_found": "Some details need checking.",
        "what_happens_next": "We will write to you.",
        "contact_info": "Call us and quote REF-1.",
    }
    assert "need a closer look" in llm.prompts[0]


async def test_plain_language_unlabelled_reply_uses_fallback(monkeypatch):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(content="No labels here.").model())

    result = await ed.explain_decision_plain_language({}, {"overall_risk_tier": "ODD"}, [])

    assert result["contact_info"].endswith("reference number: your application.")


async def test_plain_language_model_failure_uses_fallback(monkeypatch):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(error=RuntimeError("down")).model())

    result = await ed.explain_decision_plain_language({}, {}, [], "REF-9")

    assert set(result) == {"what_happened", "what_we_found", "what_happens_next", "contact_info"}
    assert "REF-9" in result["contact_info"]


# ── regulations_rag ───────────────────────────────────────────────────────────


async def test_regulations_cite_the_retrieved_passages(use_plane):
    from argus.data_plane import Passage

    class Retriever:
        async def search(self, knowledge_base, query, top=5):
            assert knowledge_base == "regulations" and top == 8
            assert query == "Q jurisdiction NL corporate pep"
            return [
                Passage("fatf-rec-12", "FATF Recommendation 12", "Rule A", "fatf.pdf", 0.75),
                Passage("weak", "Weak", "too weak", "x.pdf", 0.1),
            ]

    use_plane(retriever=Retriever())
    res = await rr.regulations_rag("Q", "NL", "corporate", ["pep"])

    assert res["source"] == "local"
    assert res["regulations"] == [
        {
            "text": "Rule A",
            "relevance": 0.75,
            "citation": {
                "knowledge_base": "regulations",
                "document": "fatf.pdf",
                "article": "FATF Recommendation 12",
                "snippet_id": "fatf-rec-12",
            },
        }
    ]


async def test_regulations_search_the_local_corpus():
    res = await rr.regulations_rag("politically exposed persons PEP", "NL", "individual", [])

    assert res["regulations"][0]["citation"]["snippet_id"] == "fatf-rec-12"


async def test_regulations_without_a_relevant_match_cite_nothing():
    res = await rr.regulations_rag("zzz", "", "", [])

    assert res["source"] == "local"
    assert res["regulations"] == []


async def test_an_unavailable_search_cites_nothing_and_says_so(use_plane, unavailable):
    use_plane(retriever=unavailable)

    res = await rr.regulations_rag("Q", "NL", "company", ["fraud"])

    assert res["source"] == "fallback"
    assert res["regulations"] == []  # an outage is not presented as regulatory evidence


async def test_a_compliance_report_without_retrieval_has_no_regulatory_triggers(
    use_plane, unavailable
):
    use_plane(retriever=unavailable)

    response = await comp.invoke(_msg({"screening": {"sanctions_hit": False}}))

    assert response["fallbacks"] == ["regulations_rag"]
    assert response["result"]["regulatory_triggers"] == []
    assert response["result"]["retrieval_queries"] == 0


async def test_compliance_agent_invoke(monkeypatch):
    import argus.agents.compliance.agent as comp

    # Patch external tool calls
    async def fake_reg(q, j, t, ri):
        return {"regulations": []}

    monkeypatch.setattr(comp, "regulations_rag", fake_reg)
    monkeypatch.setattr(
        comp,
        "risk_scorer",
        lambda i, s, c, t: {"overall": 60, "dimensions": {}},
    )
    monkeypatch.setattr(comp, "gap_analyzer", lambda ri, regs, scores: ["gap1"])

    async def fake_explain(*args, **kwargs):
        return {"text": "explanation", "source": "model"}

    monkeypatch.setattr(comp, "explain_decision", fake_explain)

    payload = {
        "entity_name": "Z",
        "entity_type": "company",
        "jurisdiction": "GB",
        "upstream_results": {
            "identity": {"result": {}},
            "screening": {
                "result": {"pep_hit": True, "findings": [{"type": "pep", "match": "John"}]}
            },
            "corporate": {"result": {"risk_flags": []}},
            "transaction": {"result": {}},
        },
    }
    msg = comp.A2AMessage(
        a2a_version="1.0", source_agent="x", target_agent="y", task_id="t3", payload=payload
    )
    res = await comp.invoke(msg)
    assert res["result"]["risk_summary"]["overall_risk_tier"] == "HIGH"
    assert res["result"]["explanation"] == "explanation"
    assert res["result"]["explanation_source"] == "model"
    assert res["source"] == "computed" and res["result"]["retrieval_queries"] == 1


def test_risk_scorer_high_risk():
    from argus.agents.compliance.tools.risk_scorer import risk_scorer

    identity = {"identity_score": 80}
    screening = {
        "screening_risk_score": 90,
        "pep_hit": True,
        "adverse_media_hit": True,
        "sanctions_hit": False,
    }
    corporate = {"corporate_score": 40, "risk_flags": ["High-risk jurisdiction: KY"]}
    transaction = {"transaction_risk_score": 60, "structuring_flag": True}
    result = risk_scorer(identity, screening, corporate, transaction)
    assert result["overall"] > 50
    assert "screening" in result["dimensions"]


def test_risk_scorer_low_risk():
    from argus.agents.compliance.tools.risk_scorer import risk_scorer

    result = risk_scorer(
        {"identity_score": 95},
        {
            "screening_risk_score": 0,
            "pep_hit": False,
            "adverse_media_hit": False,
            "sanctions_hit": False,
        },
        {"corporate_score": 90, "risk_flags": []},
        {"transaction_risk_score": 0, "structuring_flag": False},
    )
    assert result["overall"] < 40


def test_gap_analyzer_pep():
    from argus.agents.compliance.tools.gap_analyzer import gap_analyzer

    gaps = gap_analyzer(["pep"], {}, {"overall": 60})
    assert any("PEP" in g or "pep" in g.lower() or "wealth" in g.lower() for g in gaps)


def test_gap_analyzer_clean():
    from argus.agents.compliance.tools.gap_analyzer import gap_analyzer

    gaps = gap_analyzer([], {}, {"overall": 20})
    assert isinstance(gaps, list)


def test_compliance_agent_handles_none_upstream_results():
    from argus.agents.compliance.agent import app

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
    assert data["result"]["explanation_source"] == "fallback"
