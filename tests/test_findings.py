"""The canonical record must explain the policy inputs without trusting cached scores."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from argus.agents.compliance import agent as compliance
from argus.utils.demo_profiles import DEMO_PROFILES


def payload(profile):
    return {
        "entity_name": "Synthetic Test Company",
        "entity_type": "corporate",
        "jurisdiction": "NL",
        "upstream_results": {
            category: {"result": result, "source": "demo_profile", "fallbacks": []}
            for category, result in profile.items()
        },
    }


@pytest.mark.parametrize(
    ("key", "score", "tier"),
    [
        (("jane synthetic", "individual", "DE"), 3.0, "LOW"),
        (("synthetic holdings b.v.", "corporate", "NL"), 44.0, "MEDIUM"),
        (("cayman synth capital", "corporate", "KY"), 76.0, "CRITICAL"),
        (("synthetic payments ag", "corporate", "DE"), 56.5, "HIGH"),
        (("synthetic nordic bank a/s", "corporate", "DK"), 36.0, "MEDIUM"),
        (("synthetic pacific banking corporation", "corporate", "AU"), 18.2, "LOW"),
    ],
)
async def test_demo_outcomes_are_derived_from_facts(key, score, tier):
    result = (await compliance.assess(payload(DEMO_PROFILES[key]), "test"))["result"]
    assert result["risk_summary"]["overall_risk_score"] == score
    assert result["risk_summary"]["overall_risk_tier"] == tier
    assert result["decision_record"]["review_status"] == "pending"


async def test_legacy_numbers_cannot_change_a_decision():
    original = DEMO_PROFILES[("synthetic holdings b.v.", "corporate", "NL")]
    changed = deepcopy(original)
    for category, field in (
        ("identity", "identity_score"),
        ("screening", "screening_risk_score"),
        ("corporate", "corporate_score"),
        ("transaction", "transaction_risk_score"),
    ):
        changed[category][field] = 999
    a = (await compliance.assess(payload(original), "a"))["result"]
    b = (await compliance.assess(payload(changed), "b"))["result"]
    for field in ("risk_summary", "dimension_scores", "key_findings", "recommended_actions"):
        assert a[field] == b[field]
    assert [f["id"] for f in a["findings"]] == [f["id"] for f in b["findings"]]


async def test_every_fact_keeps_resolvable_evidence_and_pending_review():
    profile = DEMO_PROFILES[("cayman synth capital", "corporate", "KY")]
    result = (await compliance.assess(payload(profile), "test"))["result"]
    findings = result["findings"]
    assert {f["kind"] for f in findings} >= {
        "assessment",
        "discrepancy",
        "sanctions_match",
        "pep_match",
        "adverse_media_match",
        "corporate_flag",
        "ownership_depth",
        "structuring",
        "layering",
        "typology",
    }
    assert len({f["id"] for f in findings}) == len(findings)
    for finding in findings:
        assert finding["review_status"] == "pending"
        assert finding["policy_version"] == "argus-risk-v1"
        assert finding["evidence_refs"]
        assert all(ref in result["evidence"] for ref in finding["evidence_refs"])
    sanctions = next(f for f in findings if f["kind"] == "sanctions_match")
    assert sanctions["uncertainty"] == "potential"
    evidence = result["evidence"][sanctions["evidence_refs"][0]]
    assert evidence["data"]["citation"] == profile["screening"]["findings"][0]["citation"]
    assert evidence["source_at"] is None
    decision = result["decision_record"]
    assert decision["risk_summary"] == result["risk_summary"]
    assert decision["finding_ids"] == [f["id"] for f in findings]
    assert decision["reviewer"] is decision["decided_at"] is decision["rationale"] is None


async def test_missing_agents_are_unknown_even_when_the_numeric_default_is_low():
    result = (await compliance.assess(payload({}), "empty"))["result"]
    assert result["risk_summary"]["overall_risk_score"] == 7.0
    assert result["risk_summary"]["decision_recommendation"].startswith("Incomplete:")
    assert all(f["value"] == "not_assessed" for f in result["findings"])
    assert all(f["uncertainty"] == "unknown" for f in result["findings"])
    assert not any("No high-risk indicators" in f for f in result["key_findings"])


def test_finding_ids_ignore_observation_time_and_input_order():
    from argus.findings import collect_findings

    request = payload(
        {
            "identity": {
                "discrepancies": [
                    {"field": "name", "severity": "high", "document": "Synthetic Name A"},
                    {"field": "date_of_birth", "severity": "medium", "document": "1990-01-01"},
                ]
            }
        }
    )
    a = collect_findings(request["upstream_results"], datetime(2026, 11, 1, tzinfo=UTC))
    request["upstream_results"]["identity"]["result"]["discrepancies"].reverse()
    b = collect_findings(request["upstream_results"], datetime(2026, 11, 2, tzinfo=UTC))
    assert {f.id for f in a.findings} == {f.id for f in b.findings}
    assert set(a.evidence) == set(b.evidence)
    assert a.findings[0].observed_at != b.findings[0].observed_at


def test_empty_findings_reference_and_category_level_screening_weights():
    from argus.agents.compliance.tools.risk_scorer import risk_scorer
    from argus.findings import collect_findings

    assert risk_scorer([])["overall"] == 7.0
    records = collect_findings(
        payload(
            {
                "screening": {
                    "sanctions_hit": True,
                    "pep_hit": True,
                    "findings": [
                        {"type": "sanctions", "match": "Synthetic entry A"},
                        {"type": "sanctions", "match": "Synthetic entry B"},
                        {"type": "pep", "match": "Synthetic entry C"},
                    ],
                }
            }
        )["upstream_results"]
    )
    scores = risk_scorer(records.findings)
    assert scores["dimensions"]["screening"]["score"] == 85
    assert scores["dimensions"]["regulatory"]["score"] == 45


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"kind": "agent_score"}, "literal_error"),
        ({"category": "corporate"}, "category"),
        ({"scope": "corporate"}, "scope"),
        ({"value": False}, "value"),
        ({"policy_version": "unrecognised"}, "literal_error"),
    ],
)
def test_invalid_findings_cannot_be_replayed_as_valid_facts(changes, error):
    from pydantic import ValidationError

    from argus.findings import Finding, collect_findings

    records = collect_findings(payload({"screening": {"pep_hit": True}})["upstream_results"])
    match = next(f for f in records.findings if f.kind == "pep_match")
    with pytest.raises(ValidationError, match=error):
        Finding.model_validate({**match.model_dump(), **changes})


def test_duplicate_ids_are_rejected_instead_of_counted_twice():
    from argus.agents.compliance.tools.risk_scorer import risk_scorer
    from argus.findings import collect_findings

    records = collect_findings(
        payload({"transaction": {"typology_hits": ["Synthetic typology"]}})["upstream_results"]
    )
    finding = next(f for f in records.findings if f.kind == "typology")
    with pytest.raises(ValueError, match="Duplicate finding"):
        risk_scorer([finding, finding])


def test_screening_kind_cannot_be_relabelled_as_a_different_check():
    from pydantic import ValidationError

    from argus.findings import Finding, collect_findings

    records = collect_findings(payload({"screening": {"pep_hit": True}})["upstream_results"])
    match = next(f for f in records.findings if f.kind == "pep_match")
    with pytest.raises(ValidationError, match="scope"):
        Finding.model_validate({**match.model_dump(), "scope": "sanctions"})


@pytest.mark.parametrize("damage", ["missing_reference", "empty_references", "wrong_evidence_id"])
def test_a_replayed_record_must_resolve_its_evidence(damage):
    from pydantic import ValidationError

    from argus.findings import FindingSet, collect_findings

    records = collect_findings({})
    encoded = records.model_dump(mode="json")
    if damage == "missing_reference":
        encoded["evidence"].clear()
    elif damage == "empty_references":
        encoded["findings"][0]["evidence_refs"] = []
    else:
        next(iter(encoded["evidence"].values()))["id"] = "wrong-id"
    with pytest.raises(ValidationError, match="evidence"):
        FindingSet.model_validate(encoded)


async def test_one_missing_screening_tool_does_not_erase_the_other_hits():
    request = payload({"screening": {"sanctions_hit": False, "pep_hit": True}})
    request["upstream_results"]["screening"].update(
        source="fallback",
        fallbacks=["sanctions_checker"],
    )
    result = (await compliance.assess(request, "partial"))["result"]
    assert result["risk_summary"]["overall_risk_score"] == 25.8
    assert result["risk_summary"]["sanctions_screening"] == "not_run"
    assert result["risk_summary"]["edd_required"] is True
    states = {f["scope"]: f["value"] for f in result["findings"] if f["kind"] == "assessment"}
    assert states["sanctions"] == "not_assessed" and states["pep"] == "completed"


async def test_partial_transaction_result_keeps_the_detected_pattern_and_rule_hit():
    request = payload(
        {
            "transaction": {
                "structuring_flag": True,
                "typology_hits": [
                    {"typology": "Synthetic structuring rule", "source": "rules", "fatf_ref": ""},
                ],
            }
        }
    )
    request["upstream_results"]["transaction"].update(
        source="fallback",
        fallbacks=["typology_matcher"],
    )
    result = (await compliance.assess(request, "partial"))["result"]
    assert result["dimension_scores"]["transaction"]["score"] == 50
    assert "⚠️ Transaction assessment has missing evidence" in result["key_findings"]
    hit = next(f for f in result["findings"] if f["kind"] == "typology")
    assert result["evidence"][hit["evidence_refs"][0]]["reference"] == {}


def test_skipped_dimensions_retain_defaults_without_implying_clearance():
    from argus.agents.compliance.tools.risk_scorer import risk_scorer
    from argus.findings import collect_findings

    records = collect_findings(
        payload(
            {
                "corporate": {"skipped": True},
                "transaction": {"skipped": True},
            }
        )["upstream_results"]
    )
    scores = risk_scorer(records.findings)
    assert scores["overall"] == 7.0
    assert scores["dimensions"]["corporate_ubo"]["score"] == 20
    assert {f.value for f in records.findings if f.category == "corporate"} == {"skipped"}


def test_repeated_facts_keep_distinct_ids_and_caps_apply_in_all_dimensions():
    from argus.agents.compliance.tools.risk_scorer import risk_scorer
    from argus.findings import FindingSet, collect_findings

    records = collect_findings(
        payload(
            {
                "identity": {"discrepancies": [{"severity": "high"}] * 5},
                "screening": {"sanctions_hit": True, "pep_hit": True, "adverse_media_hit": True},
                "corporate": {"risk_flags": ["Synthetic repeated risk flag"] * 9},
                "transaction": {
                    "structuring_flag": True,
                    "layering_flag": True,
                    "typology_hits": ["A"] * 4,
                },
            }
        )["upstream_results"]
    )
    assert len({f.id for f in records.findings}) == len(records.findings)
    replay = FindingSet.model_validate_json(records.model_dump_json())
    scores = risk_scorer(replay.findings)
    assert scores["overall"] == 100.0
    assert {d["score"] for d in scores["dimensions"].values()} == {100}


def test_unrecognised_discrepancy_severity_is_recorded_as_unknown():
    from argus.findings import collect_findings

    records = collect_findings(
        payload(
            {
                "identity": {
                    "discrepancies": [
                        {"field": "name", "severity": "unrecognised"},
                    ]
                }
            }
        )["upstream_results"]
    )
    finding = next(f for f in records.findings if f.kind == "discrepancy")
    assert finding.value == "unknown" and finding.uncertainty == "unknown"
    assert records.evidence[finding.evidence_refs[0]].data["severity"] == "unrecognised"


def test_source_date_and_original_citation_are_preserved_without_changing_their_meaning():
    from argus.findings import collect_findings

    citation = {
        "document": "synthetic-source.json",
        "snippet_id": "synthetic-1",
        "published_at": "2026-01-01",
    }
    records = collect_findings(
        payload(
            {
                "screening": {
                    "adverse_media_hit": True,
                    "findings": [
                        {"type": "adverse_media", "citation": citation},
                    ],
                }
            }
        )["upstream_results"]
    )
    finding = next(f for f in records.findings if f.kind == "adverse_media_match")
    evidence = records.evidence[finding.evidence_refs[0]]
    assert finding.source_at == "2026-01-01" and evidence.reference == citation


@pytest.mark.parametrize("count", [21, 35])
async def test_layering_only_evidence_retains_the_detector_observations(monkeypatch, count):
    from argus.agents.transaction import agent as transaction
    from argus.findings import collect_findings

    transactions = [
        {"id": f"TX-SYN-{i}", "amount": 20_000, "counterparty": f"Synthetic Counterparty {i}"}
        for i in range(count)
    ]

    async def monitor(name):
        return {"source": "local", "count": count, "transactions": transactions}

    monkeypatch.setattr(transaction, "transaction_monitor", monitor)
    response = await transaction.assess({"entity_name": "Synthetic Layering Case"}, "test")
    records = collect_findings({"transaction": response})
    assert not any(f.kind == "structuring" for f in records.findings)
    finding = next(f for f in records.findings if f.kind == "layering")
    evidence = records.evidence[finding.evidence_refs[0]].data
    assert evidence["observation"]["patterns"]["unique_counterparties"] == count
    assert evidence["observation"]["patterns"]["flagged_transactions"] == []
    assert evidence["observation"]["history"]["transactions"] == transactions


async def test_corporate_flag_retains_the_observed_node_and_jurisdiction():
    from argus.agents.corporate import agent as corporate
    from argus.findings import collect_findings

    response = await corporate.assess(
        {
            "entity_name": "Harbor Test Holdings",
            "entity_type": "corporate",
            "jurisdiction": "NL",
        },
        "test",
    )
    records = collect_findings({"corporate": response})
    finding = next(f for f in records.findings if f.kind == "corporate_flag")
    evidence = records.evidence[finding.evidence_refs[0]].data
    assert evidence["ownership_node"]["name"] == "Offshore Test SPC"
    assert evidence["ownership_node"]["jurisdiction"] == "PA"
    assert evidence["jurisdiction_assessment"]["country_code"] == "PA"
    assert evidence["jurisdiction_assessment"]["fatf_risk_tier"] == "high"


def test_recorded_corporate_claims_do_not_invent_observed_ownership_nodes():
    from argus.findings import collect_findings

    profile = DEMO_PROFILES[("synthetic holdings b.v.", "corporate", "NL")]
    records = collect_findings(payload(profile)["upstream_results"])
    finding = next(f for f in records.findings if f.kind == "corporate_flag")
    evidence = records.evidence[finding.evidence_refs[0]]
    assert evidence.source == "demo_profile"
    assert evidence.data == {"reported_flag": profile["corporate"]["risk_flags"][0]}
