"""Transaction agent scoring and the typology fallback."""

from fastapi.testclient import TestClient

import agents.transaction.agent as tx
from agents.transaction.tools.pattern_detector import pattern_detector
from agents.transaction.tools.typology_matcher import _mock_typology_hits


def _msg(payload: dict) -> tx.A2AMessage:
    return tx.A2AMessage(
        a2a_version="1.0",
        source_agent="test",
        target_agent="transaction",
        task_id="t-tx",
        payload=payload,
    )


async def test_analysis_can_be_switched_off():
    response = await tx.invoke(_msg({"include_transaction_analysis": False}))

    assert response["result"]["skipped"] is True


async def test_demo_profile_short_circuits_the_tools():
    payload = {"entity_name": "Jane Synthetic", "entity_type": "individual", "jurisdiction": "DE"}
    response = await tx.invoke(_msg(payload))

    assert response["result"]["transaction_count"] == 8


async def test_no_history_scores_zero(monkeypatch):
    async def monitor(name):
        return {}

    monkeypatch.setattr(tx, "transaction_monitor", monitor)

    result = (await tx.invoke(_msg({"entity_name": "Quiet Ltd"})))["result"]

    assert result["transaction_risk_score"] == 0
    assert result["typology_hits"] == []
    assert result["structuring_flag"] is False and result["layering_flag"] is False


async def test_layering_is_scored(monkeypatch):
    async def monitor(name):
        return {"count": 1}

    async def typologies(patterns):
        return [{"typology": "Layering"}]

    monkeypatch.setattr(tx, "transaction_monitor", monitor)
    monkeypatch.setattr(tx, "pattern_detector", lambda history: {"layering_flag": True})
    monkeypatch.setattr(tx, "typology_matcher", typologies)

    result = (await tx.invoke(_msg({"entity_name": "Busy Ltd"})))["result"]

    assert result["transaction_risk_score"] == 40  # layering 30 + one typology 10


def test_health():
    assert TestClient(tx.app).get("/health").json()["service"] == "transaction"


def test_pattern_detector_without_transactions():
    assert pattern_detector({}) == {
        "structuring_flag": False,
        "layering_flag": False,
        "flagged_transactions": [],
    }


def test_mock_typology_for_layering_only():
    hits = _mock_typology_hits({"layering_flag": True})

    assert [h["typology"] for h in hits] == ["Layering via multiple counterparties"]
