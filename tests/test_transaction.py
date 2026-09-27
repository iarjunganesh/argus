"""Transaction agent scoring and the typology fallback."""

import argus.agents.transaction.agent as tx
from argus.agents.transaction.tools.pattern_detector import pattern_detector
from argus.agents.transaction.tools.typology_matcher import _rule_typology_hits


async def test_analysis_can_be_switched_off():
    response = await tx.assess({"include_transaction_analysis": False}, "t")

    assert response["result"]["skipped"] is True


async def test_no_history_scores_zero(monkeypatch):
    async def monitor(name):
        return {}

    monkeypatch.setattr(tx, "transaction_monitor", monitor)

    result = (await tx.assess({"entity_name": "Quiet Ltd"}, "t"))["result"]

    assert result["transaction_risk_score"] == 0
    assert result["typology_hits"] == []
    assert result["structuring_flag"] is False and result["layering_flag"] is False


async def test_layering_is_scored(monkeypatch):
    async def monitor(name):
        return {"count": 1}

    async def typologies(patterns):
        return {"hits": [{"typology": "Layering"}], "source": "local"}

    monkeypatch.setattr(tx, "transaction_monitor", monitor)
    monkeypatch.setattr(tx, "pattern_detector", lambda history: {"layering_flag": True})
    monkeypatch.setattr(tx, "typology_matcher", typologies)

    result = (await tx.assess({"entity_name": "Busy Ltd"}, "t"))["result"]

    assert result["transaction_risk_score"] == 40  # layering 30 + one typology 10


def test_pattern_detector_without_transactions():
    assert pattern_detector({}) == {
        "structuring_flag": False,
        "layering_flag": False,
        "flagged_transactions": [],
    }


def test_rule_typology_for_layering_only_cites_no_document():
    hits = _rule_typology_hits({"layering_flag": True})

    assert [h["typology"] for h in hits] == ["Layering via multiple counterparties"]
    assert hits[0]["fatf_ref"] == "" and hits[0]["source"] == "rules"


async def test_transaction_monitor_reads_the_local_history():
    from argus.agents.transaction.tools.transaction_monitor import transaction_monitor

    result = await transaction_monitor("Ada Synthetic")

    assert result["count"] == 6
    assert result["date_range"] == {"from": "2026-03-10", "to": "2026-03-15"}
    assert result["source"] == "local"


async def test_transaction_monitor_without_history():
    from argus.agents.transaction.tools.transaction_monitor import transaction_monitor

    result = await transaction_monitor("Nobody")

    assert result == {"count": 0, "transactions": [], "date_range": {}, "source": "local"}


async def test_typology_matcher_cites_retrieved_guidance(use_plane):
    from argus.agents.transaction.tools.typology_matcher import typology_matcher
    from argus.data_plane import Passage

    class Retriever:
        async def search(self, knowledge_base, query, top=5):
            assert knowledge_base == "regulations" and "structuring" in query
            return [
                Passage("fatf-rec-20", "FATF Recommendation 20", "Report STRs", "fatf.pdf", 0.6)
            ]

    use_plane(retriever=Retriever())
    result = await typology_matcher({"structuring_flag": True})

    assert result["source"] == "local"
    assert result["hits"] == [
        {
            "typology": "FATF Recommendation 20",
            "description": "Report STRs",
            "fatf_ref": "fatf.pdf",
            "score": 0.6,
            "source": "retrieved",
        }
    ]


async def test_typology_matcher_names_the_rule_when_nothing_is_retrieved(use_plane, unavailable):
    from argus.agents.transaction.tools.typology_matcher import typology_matcher

    use_plane(retriever=unavailable)
    result = await typology_matcher({"structuring_flag": True, "layering_flag": True})

    assert [h["source"] for h in result["hits"]] == ["rules", "rules"]
    assert result["source"] == "fallback"


async def test_an_unavailable_typology_search_marks_the_agent_as_fallback(
    monkeypatch, use_plane, unavailable
):
    async def monitor(name):
        return {"count": 7, "source": "local"}

    monkeypatch.setattr(tx, "transaction_monitor", monitor)
    monkeypatch.setattr(tx, "pattern_detector", lambda history: {"structuring_flag": True})
    use_plane(retriever=unavailable)

    response = await tx.assess({"entity_name": "Busy Ltd"}, "t")

    assert response["source"] == "fallback"
    assert response["fallbacks"] == ["typology_matcher"]
    assert response["result"]["typology_hits"][0]["source"] == "rules"


def test_pattern_detector_structuring():
    from argus.agents.transaction.tools.pattern_detector import pattern_detector

    transactions = [{"amount": 9200, "counterparty": f"Co{i}"} for i in range(7)]
    result = pattern_detector({"transactions": transactions})
    assert result["structuring_flag"] is True
    assert result["below_threshold_count"] == 7


def test_pattern_detector_clean():
    from argus.agents.transaction.tools.pattern_detector import pattern_detector

    transactions = [{"amount": 50000, "counterparty": "Big Corp"} for _ in range(5)]
    result = pattern_detector({"transactions": transactions})
    assert result["structuring_flag"] is False


async def test_transaction_agent_invoke(kyc_request):
    data = await tx.assess(kyc_request, "t")
    assert data["agent"] == "transaction"
    assert "transaction_risk_score" in data["result"]


async def test_typology_matcher_without_flags_returns_nothing():
    from argus.agents.transaction.tools import typology_matcher

    assert await typology_matcher.typology_matcher({}) == {"hits": [], "source": "local"}


async def test_transaction_monitor_falls_back_when_the_store_is_down(use_plane, unavailable):
    from argus.agents.transaction.tools.transaction_monitor import transaction_monitor

    use_plane(entities=unavailable)
    result = await transaction_monitor("Ada Synthetic")

    assert result == {"count": 0, "transactions": [], "date_range": {}, "source": "fallback"}


async def test_agent_reports_its_provenance(use_plane, unavailable):
    response = await tx.assess({"entity_name": "Ada Synthetic"}, "t")
    assert response["source"] == "computed" and response["fallbacks"] == []
    assert response["result"]["structuring_flag"] is True

    use_plane(entities=unavailable)
    response = await tx.assess({"entity_name": "Ada Synthetic"}, "t")
    assert response["source"] == "fallback"
    assert response["fallbacks"] == ["transaction_monitor"]
