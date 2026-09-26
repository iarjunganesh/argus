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
