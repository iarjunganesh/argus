"""Corporate agent scoring and the Cosmos-backed ownership tools."""

from fastapi.testclient import TestClient

import agents.corporate.agent as corp
import agents.corporate.tools.registry_lookup as reg
import agents.corporate.tools.ubo_resolver as ubo


def _msg(payload: dict) -> corp.A2AMessage:
    return corp.A2AMessage(
        a2a_version="1.0",
        source_agent="test",
        target_agent="corporate",
        task_id="t-corp",
        payload=payload,
    )


class FakeContainer:
    """Answers ownership queries from a {parent_name: [child nodes]} map."""

    def __init__(self, graph: dict):
        self.graph = graph

    def query_items(self, query, parameters, enable_cross_partition_query):
        return self.graph.get(parameters[0]["value"], [])


class FakeDB:
    def __init__(self, graph: dict):
        self.container = FakeContainer(graph)

    def get_container_client(self, name):
        return self.container


# ── agent ─────────────────────────────────────────────────────────────────────


async def test_deep_chain_without_high_risk_nodes(monkeypatch):
    async def registry(name, number):
        return {"found": True}

    async def resolver(name, registry_result):
        return {"ownership_chain": [{"name": "Sub", "jurisdiction": "NL"}], "depth": 4}

    async def jurisdictions(code):
        return {"fatf_risk_tier": "low"}

    monkeypatch.setattr(corp, "registry_lookup", registry)
    monkeypatch.setattr(corp, "ubo_resolver", resolver)
    monkeypatch.setattr(corp, "jurisdiction_mapper", jurisdictions)

    payload = {"entity_name": "Deep Holdings", "entity_type": "corporate", "jurisdiction": "NL"}
    result = (await corp.invoke(_msg(payload)))["result"]

    assert result["risk_flags"] == []
    assert result["corporate_score"] == 90  # only the depth penalty applies


async def test_demo_profile_short_circuits_the_tools():
    payload = {"entity_name": "Cayman Synth Capital", "entity_type": "corporate"}
    response = await corp.invoke(_msg({**payload, "jurisdiction": "KY"}))

    assert response["status"] == "completed"
    assert response["result"]["risk_flags"]


def test_health():
    assert TestClient(corp.app).get("/health").json()["service"] == "corporate"


# ── tools ─────────────────────────────────────────────────────────────────────


async def test_registry_lookup_reports_missing_entity(monkeypatch):
    monkeypatch.setattr(reg, "get_cosmos_database", lambda: FakeDB({}))

    assert await reg.registry_lookup("Unknown Ltd", None) == {"found": False, "record": None}


async def test_ubo_resolver_recurses_through_corporate_owners(monkeypatch):
    graph = {
        "Parent": [
            {"name": "Sub", "entity_type": "corporate", "ownership_percentage": 100},
        ],
        "Sub": [
            {"name": "Owner", "entity_type": "individual", "ownership_percentage": 60},
            {"name": "Minor", "entity_type": "individual", "ownership_percentage": 10},
        ],
    }
    monkeypatch.setattr(ubo, "get_cosmos_database", lambda: FakeDB(graph))

    result = await ubo.ubo_resolver("Parent", {})

    assert [u["name"] for u in result["ubos"]] == ["Owner"]
    assert result["ubos"][0]["depth"] == 2
    assert [n["name"] for n in result["ownership_chain"]] == ["Sub", "Owner", "Minor"]


async def test_ubo_resolver_stops_at_max_depth():
    result = await ubo.ubo_resolver("Anything", {}, depth=ubo.MAX_DEPTH)

    assert result == {
        "ubos": [],
        "ownership_chain": [],
        "depth": ubo.MAX_DEPTH,
        "note": "Max depth reached",
    }
