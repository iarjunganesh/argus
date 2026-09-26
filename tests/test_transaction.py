"""Transaction agent scoring and the typology fallback."""

from fastapi.testclient import TestClient

import argus.agents.transaction.agent as tx
from argus.agents.transaction.tools.pattern_detector import pattern_detector
from argus.agents.transaction.tools.typology_matcher import _mock_typology_hits


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


async def test_transaction_monitor_db_hit(monkeypatch):
    import argus.agents.transaction.tools.transaction_monitor as tm

    class FakeContainer:
        def query_items(self, query=None, parameters=None, enable_cross_partition_query=False):
            return [
                {"id": "T1", "amount": 5000, "date": "2026-01-10", "counterparty": "Alpha"},
                {"id": "T2", "amount": 3000, "date": "2026-02-15", "counterparty": "Beta"},
            ]

    class FakeDB:
        def get_container_client(self, name):
            return FakeContainer()

    monkeypatch.setattr(tm, "get_cosmos_database", lambda: FakeDB())
    result = await tm.transaction_monitor("TestCorp")
    assert result["count"] == 2
    assert result["date_range"]["from"] == "2026-01-10"
    assert result["date_range"]["to"] == "2026-02-15"


async def test_transaction_monitor_db_empty(monkeypatch):
    import argus.agents.transaction.tools.transaction_monitor as tm

    class FakeContainer:
        def query_items(self, query=None, parameters=None, enable_cross_partition_query=False):
            return []

    class FakeDB:
        def get_container_client(self, name):
            return FakeContainer()

    monkeypatch.setattr(tm, "get_cosmos_database", lambda: FakeDB())
    result = await tm.transaction_monitor("Nobody")
    assert result["count"] == 0
    assert result["transactions"] == []


async def test_typology_matcher_search_hit(monkeypatch):
    import argus.agents.transaction.tools.typology_matcher as tmt

    class FakeResult:
        def __init__(self, hits):
            self._hits = hits

        def __iter__(self):
            return iter(self._hits)

    class FakeClient:
        def search(self, search_text=None, top=None):
            return FakeResult(
                [
                    {
                        "typology_name": "Smurfing",
                        "description": "Cash structuring below threshold",
                        "fatf_reference": "FATF-2023-3.2",
                        "@search.score": 0.95,
                    }
                ]
            )

    monkeypatch.setattr(tmt, "get_search_client", lambda index: FakeClient())
    hits = await tmt.typology_matcher({"structuring_flag": True})
    assert hits
    assert hits[0]["typology"] == "Smurfing"


async def test_typology_matcher_regulations_fallback(monkeypatch):
    import argus.agents.transaction.tools.typology_matcher as tmt

    call_count = 0

    class EmptyResult:
        def __iter__(self):
            return iter([])

    class RegResult:
        def __iter__(self):
            return iter(
                [
                    {
                        "title": "Layering typology",
                        "content": "Multi-hop rapid movement",
                        "source_doc": "FATF-4.1",
                        "@search.score": 0.88,
                    }
                ]
            )

    class FakeClient:
        def search(self, search_text=None, top=None):
            nonlocal call_count
            call_count += 1
            return EmptyResult() if call_count == 1 else RegResult()

    monkeypatch.setattr(tmt, "get_search_client", lambda index: FakeClient())
    hits = await tmt.typology_matcher({"layering_flag": True})
    assert hits
    assert "typology" in hits[0]


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


def test_transaction_agent_invoke(a2a_request):
    from argus.agents.transaction.agent import app

    client = TestClient(app)
    resp = client.post(
        "/a2a/invoke", json={**a2a_request, "target_agent": "argus-transaction-agent-v1"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "transaction"
    assert "transaction_risk_score" in data["result"]


async def test_typology_matcher_without_flags_returns_nothing():
    from argus.agents.transaction.tools import typology_matcher

    assert await typology_matcher.typology_matcher({}) == []


async def test_typology_matcher_falls_back_to_mock_hits(monkeypatch):
    import argus.agents.transaction.tools.typology_matcher as tmt

    def no_search(index):
        raise RuntimeError("no search")

    monkeypatch.setattr(tmt, "get_search_client", no_search)

    assert await tmt.typology_matcher({"structuring_flag": True})


async def test_transaction_monitor_falls_back_to_mock_without_cosmos(monkeypatch):
    import argus.agents.transaction.tools.transaction_monitor as tm

    def no_db():
        raise RuntimeError("no db")

    monkeypatch.setattr(tm, "get_cosmos_database", no_db)

    assert (await tm.transaction_monitor("Someone"))["source"] == "mock"
