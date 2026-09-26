"""Screening agent scoring and its three data-plane tools."""

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


# ── tools ─────────────────────────────────────────────────────────────────────


async def test_sanctions_match_on_a_listed_name_with_its_citation():
    result = await sc.sanctions_checker("Viktor Testovich", [], "RU")

    assert result["hit"] is True and result["source"] == "local"
    first = result["findings"][0]
    assert first["citation"] == {
        "knowledge_base": "sanctions",
        "document": "OFAC_SDN",
        "snippet_id": "SYN-T-1",
        "program": "RUSSIA",
        "is_active": True,
    }


async def test_sanctions_no_match_for_an_unlisted_name():
    result = await sc.sanctions_checker("Ada Synthetic", [], "NL")

    assert result == {"hit": False, "findings": [], "source": "local"}


async def test_adverse_media_finds_negative_coverage_only():
    result = await am.adverse_media_scanner("Harbor Test Holdings", [])

    assert result["hit"] is True
    assert result["findings"][0]["citation"]["snippet_id"] == "NEWS-T1"
    assert result["findings"][0]["citation"]["tags"] == ["fraud"]
    snippets = {f["citation"]["snippet_id"] for f in result["findings"]}
    assert "NEWS-T2" not in snippets  # positive coverage is never indexed


@pytest.mark.parametrize(
    "call",
    [
        lambda: sc.sanctions_checker("Viktor Testovich", [], ""),
        lambda: am.adverse_media_scanner("Harbor Test Holdings", []),
    ],
)
async def test_search_tools_fall_back_when_search_is_down(use_plane, unavailable, call):
    use_plane(retriever=unavailable)

    assert await call() == {"hit": False, "findings": [], "source": "fallback"}


async def test_pep_checker_finds_a_listed_pep():
    import argus.agents.screening.tools.pep_checker as pc

    result = await pc.pep_checker("Pat Politico", "", "")

    assert result["hit"] is True
    assert result["findings"][0]["match"] == "Pat Politico — Deputy minister (FR, 2015-2020)"
    assert result["findings"][0]["source"] == "local_entities"


async def test_pep_checker_ignores_people_who_are_not_peps():
    import argus.agents.screening.tools.pep_checker as pc

    assert await pc.pep_checker("Ada Synthetic", "", "NL") == {
        "hit": False,
        "findings": [],
        "source": "local",
    }


async def test_pep_checker_falls_back_when_the_store_is_down(use_plane, unavailable):
    import argus.agents.screening.tools.pep_checker as pc

    use_plane(entities=unavailable)

    assert (await pc.pep_checker("Pat Politico", "", ""))["source"] == "fallback"


async def test_agent_counts_only_searches_that_answered(use_plane, unavailable):
    response = await screening.invoke(_msg({"entity_name": "Viktor Testovich"}))
    assert response["source"] == "computed"
    assert response["result"]["retrieval_queries"] == 2
    assert response["result"]["sanctions_hit"] is True

    use_plane(retriever=unavailable)
    response = await screening.invoke(_msg({"entity_name": "Viktor Testovich"}))
    assert response["source"] == "fallback"
    assert response["fallbacks"] == ["adverse_media_scanner", "sanctions_checker"]
    assert response["result"]["retrieval_queries"] == 0


async def test_demo_profile_is_labelled():
    payload = {"entity_name": "Wirecard AG", "entity_type": "corporate", "jurisdiction": "DE"}

    assert (await screening.invoke(_msg(payload)))["source"] == "demo_profile"


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


def test_a_hit_needs_every_word_of_a_name_or_alias():
    from argus.agents.screening.tools.name_match import mentions

    assert mentions("Daniel Doyle was listed.", ["Daniel Doyle"])
    assert mentions("Known as V. Testovich.", ["Viktor Testovich", "V. Testovich"])
    assert not mentions("Daniel Craig was listed.", ["Daniel Doyle"])
    assert not mentions("Anything", ["", "  "])


async def test_a_first_name_alone_is_not_a_sanctions_match():
    result = await sc.sanctions_checker("Viktor Someone", [], "RU")

    assert result == {"hit": False, "findings": [], "source": "local"}
