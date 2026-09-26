"""Screening agent scoring and the Foundry IQ result parsing shared by its tools."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import argus.agents.screening.agent as screening
import argus.agents.screening.tools.adverse_media_scanner as am
import argus.agents.screening.tools.sanctions_checker as sc


def _msg(payload: dict) -> screening.A2AMessage:
    return screening.A2AMessage(
        a2a_version="1.0",
        source_agent="test",
        target_agent="screening",
        task_id="t-scr",
        payload=payload,
    )


def _tool(hit: bool, kind: str):
    async def run(*args):
        return {"hit": hit, "findings": [{"type": kind}] if hit else []}

    return run


async def test_all_hits_are_scored_and_capped(monkeypatch):
    monkeypatch.setattr(screening, "sanctions_checker", _tool(True, "sanctions"))
    monkeypatch.setattr(screening, "adverse_media_scanner", _tool(True, "adverse_media"))
    monkeypatch.setattr(screening, "pep_checker", _tool(True, "pep"))

    result = (await screening.invoke(_msg({"entity_name": "Nobody Known"})))["result"]

    assert result["screening_risk_score"] == 100
    assert [f["type"] for f in result["findings"]] == ["sanctions", "adverse_media", "pep"]
    assert result["sanctions_hit"] and result["adverse_media_hit"] and result["pep_hit"]


async def test_demo_profile_short_circuits_the_tools(monkeypatch):
    monkeypatch.setattr(screening, "sanctions_checker", None)  # would fail if called

    payload = {"entity_name": "Wirecard AG", "entity_type": "corporate", "jurisdiction": "DE"}
    response = await screening.invoke(_msg(payload))

    assert response["result"]["adverse_media_hit"] is True


def test_health():
    assert TestClient(screening.app).get("/health").json()["service"] == "screening"


# ── Foundry IQ result parsing (same shape in both tools) ─────────────────────


def _foundry(items):
    kb = SimpleNamespace(query=lambda **kwargs: SimpleNamespace(items=items))
    return lambda: SimpleNamespace(knowledge_bases=kb)


ITEMS = [
    # Object-shaped item, score on the 0–4 reranker scale, metadata already a dict.
    SimpleNamespace(
        relevance_score=2.0,
        content="Match one",
        citation=SimpleNamespace(document_title="list.pdf", snippet_id="s1"),
        metadata={"program": "EU", "is_active": True, "tags": ["fraud"]},
        id="1",
    ),
    # Dict-shaped item with no citation and unreadable metadata.
    {"relevance_score": 0.4, "content": "Match two", "metadata_json": "{not json", "id": "2"},
    # Below the 0.2 threshold: ignored.
    {"relevance_score": 0.1, "content": "noise", "id": "3"},
]


@pytest.mark.parametrize("module", [am, sc])
async def test_items_parse_from_objects_and_dicts(monkeypatch, module):
    monkeypatch.setattr(module, "get_foundry_client", _foundry(ITEMS))

    if module is am:
        result = await module.adverse_media_scanner("X", [])
    else:
        result = await module.sanctions_checker("X", [], "")

    assert result["hit"] is True
    first, second = result["findings"]
    assert first["confidence"] == 0.5
    assert first["foundry_iq_citation"]["document"] == "list.pdf"
    assert first["foundry_iq_citation"]["snippet_id"] == "s1"
    assert second["foundry_iq_citation"]["document"] == "unknown"
    assert second["foundry_iq_citation"]["snippet_id"] == "2"
    if module is am:
        assert first["foundry_iq_citation"]["tags"] == ["fraud"]
        assert second["foundry_iq_citation"]["tags"] == []
    else:
        assert first["foundry_iq_citation"]["program"] == "EU"
        assert second["foundry_iq_citation"]["program"] is None


@pytest.mark.parametrize("module", [am, sc])
def test_metadata_of_wrong_type_is_ignored(module):
    assert module._load_metadata({"metadata_json": ["not", "a", "string"]}) == {}


async def test_adverse_and_sanctions_positive(monkeypatch):
    import argus.agents.screening.tools.adverse_media_scanner as am
    import argus.agents.screening.tools.sanctions_checker as sc

    class FakeKB:
        def query(self, knowledge_base_name=None, query=None, top=0, include_citations=False):
            return {
                "items": [
                    {
                        "relevance_score": 0.6,
                        "content": "bad news about X",
                        "citation": {"document_title": "news.pdf", "snippet_id": "nid"},
                        "metadata_json": '{"published_at": "2025-01-01", "tags": ["fraud"]}',
                        "id": "x1",
                    }
                ]
            }

    class FakeClient:
        knowledge_bases = FakeKB()

    monkeypatch.setattr(am, "get_foundry_client", lambda: FakeClient())
    monkeypatch.setattr(sc, "get_foundry_client", lambda: FakeClient())

    ares = await am.adverse_media_scanner("X", ["X"])
    assert ares["hit"] is True

    sres = await sc.sanctions_checker("X", ["X"], "NL")
    assert sres["hit"] is True


async def test_screening_tools_mock_and_metadata(monkeypatch):
    import argus.agents.screening.tools.adverse_media_scanner as am
    import argus.agents.screening.tools.sanctions_checker as sc

    # Patch get_foundry_client to raise
    monkeypatch.setattr(
        am, "get_foundry_client", lambda: (_ for _ in ()).throw(RuntimeError("no client"))
    )
    monkeypatch.setattr(
        sc, "get_foundry_client", lambda: (_ for _ in ()).throw(RuntimeError("no client"))
    )

    r = await am.adverse_media_scanner("Alice", ["A"])
    assert r["source"] == "mock"

    s = await sc.sanctions_checker("Alice", ["A"], "NL")
    assert s["source"] == "mock"


async def test_pep_checker_db_hit(monkeypatch):
    import argus.agents.screening.tools.pep_checker as pc

    class FakeContainer:
        def query_items(self, query=None, parameters=None, enable_cross_partition_query=False):
            return [
                {"name": "John Doe", "role": "Minister", "country": "DE", "period": "2020-2024"}
            ]

    class FakeDB:
        def get_container_client(self, name):
            return FakeContainer()

    monkeypatch.setattr(pc, "get_cosmos_database", lambda: FakeDB())
    result = await pc.pep_checker("John Doe", "1970-01-01", "DE")
    assert result["hit"] is True
    assert result["findings"][0]["type"] == "pep"
    assert "Minister" in result["findings"][0]["match"]


async def test_pep_checker_db_no_hit(monkeypatch):
    import argus.agents.screening.tools.pep_checker as pc

    class FakeContainer:
        def query_items(self, query=None, parameters=None, enable_cross_partition_query=False):
            return []

    class FakeDB:
        def get_container_client(self, name):
            return FakeContainer()

    monkeypatch.setattr(pc, "get_cosmos_database", lambda: FakeDB())
    result = await pc.pep_checker("Jane Clean", "", "US")
    assert result["hit"] is False
    assert result["findings"] == []


def test_screening_agent_invoke(a2a_request):
    from argus.agents.screening.agent import app

    client = TestClient(app)
    resp = client.post(
        "/a2a/invoke", json={**a2a_request, "target_agent": "argus-screening-agent-v1"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "screening"
    assert data["status"] == "completed"
    assert "screening_risk_score" in data["result"]
