"""Compliance agent and its tools: tiering, findings, actions, explanations, regulations."""

from types import SimpleNamespace

import argus.agents.compliance.agent as comp
import argus.agents.compliance.tools.explain_decision as ed
import argus.agents.compliance.tools.regulations_rag as rr
from argus import decision
from argus.agents.compliance.tools.gap_analyzer import gap_analyzer
from argus.agents.compliance.tools.risk_scorer import risk_scorer
from argus.findings import collect_findings


def _payload(upstream: dict) -> dict:
    return {
        "entity_name": "Acme",
        "entity_type": "corporate",
        "jurisdiction": "NL",
        "upstream_results": {k: {"result": v} for k, v in upstream.items()},
    }


class FakeLLM:
    """Stands in for AsyncOpenAI: records the prompt and returns fixed content."""

    def model(self, reasoning: bool = False):
        """This client as the configured chat model, for patching `get_chat_model`."""
        from argus.models import ChatModel

        return lambda: ChatModel("test", "test-model", self, reasoning=reasoning)

    def __init__(
        self,
        content: str | None = None,
        error: Exception | None = None,
        failures: int | None = None,
        response: dict | None = None,
    ):
        self.content = content
        self.error = error
        # How many calls raise `error` before the rest answer; None: every call raises it.
        self.failures = failures
        # Extra attributes of the response, such as `model`, `id` and `usage`.
        self.response = response or {}
        self.prompts: list[str] = []
        self.calls: list[dict] = []
        # The client options each call was made with (`AsyncOpenAI.with_options`).
        self.options: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def with_options(self, **options):
        self.options.append(options)
        return self

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        self.prompts.append(kwargs["messages"][0]["content"])
        if self.error and (self.failures is None or len(self.calls) <= self.failures):
            raise self.error
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], **self.response)


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

    result = (await comp.assess(_payload(upstream), "t"))["result"]

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
        "identity": {"discrepancies": [{"field": "name", "severity": "high"}] * 3},
        "screening": {
            "pep_hit": True,
            "screening_risk_score": 60,
            "findings": [{"type": "adverse_media", "match": "ignored"}, {"type": "pep"}],
        },
        "corporate": {"risk_flags": []},
        "transaction": {"structuring_flag": False},
    }

    result = (await comp.assess(_payload(upstream), "t"))["result"]

    assert result["risk_summary"]["overall_risk_tier"] == "MEDIUM"
    assert result["risk_summary"]["overall_risk_score"] == 36.8
    assert result["key_findings"][0] == "PEP identified: "
    assert not any(f["kind"] == "adverse_media_match" for f in result["findings"])


async def test_clean_entity_is_low_risk_with_default_action():
    upstream = {
        "identity": {"discrepancies": []},
        "screening": {"sanctions_hit": False},
        "corporate": {"risk_flags": []},
        "transaction": {"structuring_flag": False},
    }
    result = (await comp.assess(_payload(upstream), "t"))["result"]

    assert result["risk_summary"]["overall_risk_tier"] == "LOW"
    assert result["risk_summary"]["sanctions_screening"] == "no_match"
    assert result["risk_summary"]["decision_recommendation"].startswith("Standard onboarding")
    assert result["key_findings"] == [
        "No high-risk indicators found in the assessed checks; human review remains pending"
    ]
    assert result["recommended_actions"] == ["Continue standard periodic review cycle"]


async def test_a_sanctions_match_alone_holds_the_case_whatever_the_score():
    screening = {"sanctions_hit": True, "screening_risk_score": 60, "findings": []}

    result = (await comp.assess(_payload({"screening": screening}), "t"))["result"]

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
        payload = _payload({})
        payload["upstream_results"]["screening"] = screening

        result = (await comp.assess(payload, "t"))["result"]

        summary = result["risk_summary"]
        assert summary["sanctions_screening"] == "not_run"
        assert summary["tier_basis"] == "score"
        assert summary["decision_recommendation"].startswith("Incomplete:")
        assert "⚠️ Sanctions screening did not run" in result["key_findings"]
        assert (
            "Run sanctions screening before any onboarding decision"
            in (result["recommended_actions"])
        )


async def test_a_pep_match_requires_enhanced_due_diligence_whatever_the_tier():
    screening = {"pep_hit": True, "screening_risk_score": 25, "findings": [{"type": "pep"}]}

    result = (await comp.assess(_payload({"screening": screening}), "t"))["result"]

    summary = result["risk_summary"]
    assert summary["overall_risk_tier"] == "LOW"  # a PEP match does not raise the tier
    assert summary["tier_basis"] == "score"
    assert summary["edd_required"] is True
    assert summary["decision_recommendation"].startswith("Enhanced Due Diligence required")
    assert "Apply enhanced ongoing monitoring to the relationship" in result["recommended_actions"]
    assert "enhanced due diligence is required before onboarding" in result["explanation"]


async def test_a_case_without_a_pep_match_does_not_require_edd_by_rule():
    result = (await comp.assess(_payload({"screening": {"sanctions_hit": False}}), "t"))["result"]

    assert result["risk_summary"]["edd_required"] is False


def test_the_sanctions_hold_and_critical_tier_outrank_the_edd_recommendation():
    assert decision.recommendation("LOW", decision.POTENTIAL_MATCH, True).startswith("Hold:")
    assert decision.recommendation("LOW", decision.NOT_RUN, True).startswith("Incomplete:")
    assert decision.recommendation("CRITICAL", decision.NO_MATCH, True).startswith("Do not onboard")


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
    assert decision.recommendation("UNKNOWN") == "Review required."


# ── risk scorer and gap analyzer ──────────────────────────────────────────────


def test_adverse_media_only_case_gets_no_boost():
    screening = {"adverse_media_hit": True, "screening_risk_score": 70}
    adverse_only = risk_scorer(
        collect_findings(_payload({"screening": screening})["upstream_results"]).findings
    )
    with_pep = risk_scorer(
        collect_findings(
            _payload(
                {
                    "screening": {**screening, "pep_hit": True},
                }
            )["upstream_results"]
        ).findings
    )

    # Cached screening score 70 is ignored: the media flag scores 15. No extra boost.
    assert adverse_only["overall"] == 20.2  # identity 4 + screening 4.5 + corporate 3 + reg 8.75
    assert with_pep["overall"] == 39.0  # 4 + 12 + 3 + 20
    assert adverse_only["dimensions"]["regulatory"]["tier"] == "MEDIUM"


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
    assert (llm.calls[0]["max_tokens"], llm.calls[0]["temperature"]) == (250, 0.2)
    assert "FATF Rec.12" in llm.prompts[0]
    assert "- Identity: 10/100" in llm.prompts[0]
    assert "Tier set by: the score band" in llm.prompts[0]
    assert "Sanctions screening: not reported" in llm.prompts[0]
    assert "Enhanced due diligence: not required by a rule" in llm.prompts[0]


async def test_a_reasoning_model_gets_a_completion_budget_and_no_temperature(monkeypatch):
    from argus.models import REASONING_COMPLETION_TOKENS

    llm = FakeLLM(content="Rated LOW.")
    monkeypatch.setattr(ed, "get_chat_model", llm.model(reasoning=True))

    explanation = await ed.explain_decision(
        {"name": "Acme"}, {"overall_risk_tier": "LOW"}, {}, [], []
    )
    letter = await ed.explain_decision_plain_language({}, {"overall_risk_tier": "LOW"}, [])

    assert explanation["source"] == "model"
    assert letter
    for call in llm.calls:
        assert call["max_completion_tokens"] == REASONING_COMPLETION_TOKENS
        assert "max_tokens" not in call and "temperature" not in call


async def test_the_model_is_told_when_enhanced_due_diligence_is_required(monkeypatch):
    llm = FakeLLM(content="EDD required.")
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    await ed.explain_decision({}, {"overall_risk_tier": "LOW", "edd_required": True}, {}, [], [])

    assert "Enhanced due diligence: required (PEP match), whatever the tier" in llm.prompts[0]


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


ENTITY = {"name": "Acme", "type": "corporate", "jurisdiction": "NL"}
SUMMARY = {"overall_risk_tier": "HIGH", "overall_risk_score": 60, "edd_required": True}


async def test_the_analyst_request_is_what_the_explanation_sends(monkeypatch):
    llm = FakeLLM(content="Rated HIGH.")
    monkeypatch.setattr(ed, "get_chat_model", llm.model())
    args = (ENTITY, SUMMARY, {"identity": {"score": 10}}, ["PEP identified"], [{"rule": "R1"}])

    request = ed.analyst_request(*args)
    await ed.explain_decision(*args)
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(error=RuntimeError("down")).model())
    fallback = await ed.explain_decision(*args)

    assert llm.prompts == [request.prompt]
    assert fallback == {"text": request.fallback, "source": "fallback"}


async def test_a_model_call_records_its_request_response_and_usage(monkeypatch):
    usage = SimpleNamespace(
        model_dump=lambda exclude_none: {"prompt_tokens": 700, "completion_tokens": 90}
    )
    llm = FakeLLM(
        content="  Rated HIGH.  ",
        response={"model": "test-model-2026-01-01", "id": "resp-1", "usage": usage},
    )
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    call = await ed.request_explanation(ed.analyst_request(ENTITY, SUMMARY, {}, [], []))

    assert (call.text, call.source, call.error, call.error_kind) == (
        "Rated HIGH.",
        "model",
        None,
        None,
    )
    assert call.request == llm.calls[0]
    assert call.request["model"] == "test-model"
    assert call.request["max_tokens"] == ed.MAX_TOKENS
    assert call.request["temperature"] == ed.TEMPERATURE
    assert (call.response_model, call.response_id) == ("test-model-2026-01-01", "resp-1")
    assert call.usage == {"prompt_tokens": 700, "completion_tokens": 90}
    assert call.latency_seconds is not None and call.latency_seconds >= 0


async def test_usage_without_a_pydantic_model_is_read_from_its_fields(monkeypatch):
    llm = FakeLLM(content="Rated LOW.", response={"usage": SimpleNamespace(total_tokens=5)})
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    call = await ed.request_explanation(ed.analyst_request({}, {}, {}, [], []))

    assert call.usage == {"total_tokens": 5}
    assert (call.response_model, call.response_id) == (None, None)


async def test_a_failed_call_records_the_error_and_falls_back(monkeypatch):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(error=TimeoutError("timed out")).model())
    request = ed.analyst_request({}, {"overall_risk_tier": "LOW"}, {}, [], [])

    call = await ed.request_explanation(request)

    assert (call.text, call.source, call.error_kind) == (request.fallback, "fallback", "call")
    assert call.error == "TimeoutError: timed out"
    assert call.request is not None and call.usage is None
    assert call.latency_seconds is not None


async def test_without_a_model_nothing_is_sent():
    request = ed.analyst_request({}, {"overall_risk_tier": "LOW"}, {}, [], [])

    call = await ed.request_explanation(request)

    assert (call.source, call.error_kind, call.request, call.latency_seconds) == (
        "fallback",
        "unavailable",
        None,
        None,
    )
    assert call.error == "ModelUnavailable: ARGUS_MODEL_PROVIDER is none"


async def test_a_study_call_turns_off_the_clients_own_retries(monkeypatch):
    llm = FakeLLM(content="Rated LOW.")
    monkeypatch.setattr(ed, "get_chat_model", llm.model())
    request = ed.analyst_request({}, {}, {}, [], [])

    await ed.request_explanation(request)
    assert llm.options == []  # the live explanation keeps the client's defaults
    await ed.request_explanation(request, client_retries=0)
    assert llm.options == [{"max_retries": 0}]


def test_the_openai_client_retries_unless_told_not_to():
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key="test", base_url="http://127.0.0.1:9")

    assert client.max_retries == 2
    assert client.with_options(max_retries=0).max_retries == 0


async def test_an_empty_reply_is_recorded_as_empty(monkeypatch):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(content=None).model())

    call = await ed.request_explanation(ed.analyst_request({}, {}, {}, [], []))

    assert (call.source, call.error_kind, call.error) == ("fallback", "empty", "empty reply")


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

    response = await comp.assess(_payload({"screening": {"sanctions_hit": False}}), "t")

    assert response["fallbacks"] == ["regulations_rag"]
    assert response["result"]["regulatory_triggers"] == []
    assert response["result"]["retrieval_queries"] == 0


async def test_compliance_agent_invoke(monkeypatch):
    import argus.agents.compliance.agent as comp

    # Patch external tool calls
    async def fake_reg(q, j, t, ri):
        return {"regulations": []}

    monkeypatch.setattr(comp, "regulations_rag", fake_reg)

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
    res = await comp.assess(payload, "t3")
    assert res["result"]["risk_summary"]["overall_risk_tier"] == "LOW"
    assert res["result"]["explanation"] == "explanation"
    assert res["result"]["explanation_source"] == "model"
    assert res["source"] == "computed" and res["result"]["retrieval_queries"] == 1


def test_risk_scorer_high_risk():
    from argus.agents.compliance.tools.risk_scorer import risk_scorer

    identity = {"discrepancies": [{"field": "name", "severity": "high"}] * 3}
    screening = {
        "screening_risk_score": 90,
        "pep_hit": True,
        "adverse_media_hit": True,
        "sanctions_hit": False,
    }
    corporate = {"risk_flags": ["High-risk node: Synthetic Owner A", "High-risk node: Synthetic B"]}
    transaction = {"structuring_flag": True, "layering_flag": True, "typology_hits": ["A", "B"]}
    records = collect_findings(
        _payload(
            {
                "identity": identity,
                "screening": screening,
                "corporate": corporate,
                "transaction": transaction,
            }
        )["upstream_results"]
    )
    result = risk_scorer(records.findings)
    assert result["overall"] == 68.5
    assert "screening" in result["dimensions"]


def test_risk_scorer_low_risk():
    from argus.agents.compliance.tools.risk_scorer import risk_scorer

    records = collect_findings(
        _payload(
            {
                "identity": {"discrepancies": [{"field": "date_of_birth", "severity": "medium"}]},
                "screening": {
                    "screening_risk_score": 0,
                    "pep_hit": False,
                    "adverse_media_hit": False,
                    "sanctions_hit": False,
                },
                "corporate": {"risk_flags": []},
                "transaction": {"structuring_flag": False},
            }
        )["upstream_results"]
    )
    assert risk_scorer(records.findings)["overall"] == 2.0


def test_gap_analyzer_pep():
    from argus.agents.compliance.tools.gap_analyzer import gap_analyzer

    gaps = gap_analyzer(["pep"], {}, {"overall": 60})
    assert any("PEP" in g or "pep" in g.lower() or "wealth" in g.lower() for g in gaps)


def test_gap_analyzer_clean():
    from argus.agents.compliance.tools.gap_analyzer import gap_analyzer

    gaps = gap_analyzer([], {}, {"overall": 20})
    assert isinstance(gaps, list)


async def test_compliance_agent_handles_none_upstream_results():
    payload = {
        "entity_name": "Synthetic Entity Ltd.",
        "entity_type": "corporate",
        "jurisdiction": "KY",
        "upstream_results": {
            "identity": {"status": "error", "result": None},
            "screening": {"status": "error", "result": None},
            "corporate": {"status": "completed", "result": {}},
            "transaction": {"status": "completed", "result": {}},
        },
    }

    data = await comp.assess(payload, "test-task-none-upstream")
    assert data["status"] == "completed"
    assert "risk_summary" in data["result"]
    assert "explanation" in data["result"]
    assert data["result"]["explanation_source"] == "fallback"


# ── regulatory triggers ──────────────────────────────────────────────────────


def test_a_trigger_states_the_passages_first_sentence_whole():
    passage = "FATF Recommendation 12: apply EDD to PEPs (Rec. 12). Senior approval is required."
    assert comp.rule_statement(passage) == "FATF Recommendation 12: apply EDD to PEPs (Rec. 12)."
    assert comp.rule_statement("  One sentence without an end  ") == "One sentence without an end"
    assert comp.rule_statement("") == ""


def test_a_long_first_sentence_is_cut_at_a_word_and_marked():
    sentence = "Article 2 lists offences: " + "; ".join(["fraud", "forgery", "piracy"] * 30) + "."
    rule = comp.rule_statement(sentence, limit=60)
    assert rule == "Article 2 lists offences: fraud; forgery; piracy; fraud…"
    assert len(rule) <= 61


async def test_every_regulation_in_the_corpus_gives_a_whole_rule():
    from argus.data_plane.corpus import REGULATION_DOCUMENTS

    for document in REGULATION_DOCUMENTS:
        rule = comp.rule_statement(document["content"])
        assert rule.endswith((".", "…")), rule
        assert len(rule) <= comp.RULE_MAX_CHARS + 1
