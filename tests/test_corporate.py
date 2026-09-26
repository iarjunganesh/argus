"""Corporate agent scoring and the Cosmos-backed ownership tools."""

from fastapi.testclient import TestClient

import argus.agents.corporate.agent as corp
import argus.agents.corporate.tools.registry_lookup as reg
import argus.agents.corporate.tools.ubo_resolver as ubo


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


async def test_corporate_agent_invoke(monkeypatch):
    import argus.agents.corporate.agent as corp

    # Patch dependent functions
    monkeypatch.setattr(corp, "get_demo_profile", lambda name, etype, j: None)

    async def fake_registry(name, rn):
        return {"found": True}

    async def fake_ubo(name, rr):
        return {"ownership_chain": [{"name": "X", "jurisdiction": "GB"}], "depth": 1}

    monkeypatch.setattr(corp, "registry_lookup", fake_registry)
    monkeypatch.setattr(corp, "ubo_resolver", fake_ubo)

    async def fake_jmap(j):
        return {"fatf_risk_tier": "high"}

    monkeypatch.setattr(corp, "jurisdiction_mapper", fake_jmap)

    msg = corp.A2AMessage(
        a2a_version="1.0",
        source_agent="x",
        target_agent="y",
        task_id="t1",
        payload={"entity_name": "Acme", "entity_type": "corporate", "jurisdiction": "GB"},
    )
    res = await corp.invoke(msg)
    assert res["result"]["corporate_score"] <= 100


async def test_jurisdiction_high_risk():
    from argus.agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper

    result = await jurisdiction_mapper("KY")
    assert result["fatf_risk_tier"] == "high"
    assert len(result["special_measures"]) > 0


async def test_jurisdiction_low_risk():
    from argus.agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper

    result = await jurisdiction_mapper("SE")
    assert result["fatf_risk_tier"] == "low"


async def test_jurisdiction_medium_risk():
    from argus.agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper

    result = await jurisdiction_mapper("ng")
    assert result["country_code"] == "NG"
    assert result["fatf_risk_tier"] == "medium"
    assert "monitoring" in result["special_measures"][0].lower()


async def test_jurisdiction_unknown_when_missing_code():
    from argus.agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper

    result = await jurisdiction_mapper("")
    assert result["country_code"] == ""
    assert result["fatf_risk_tier"] == "unknown"
    assert result["special_measures"] == []


def test_corporate_agent_skips_individual(a2a_request):
    from argus.agents.corporate.agent import app

    client = TestClient(app)
    payload = {**a2a_request, "payload": {**a2a_request["payload"], "entity_type": "individual"}}
    resp = client.post("/a2a/invoke", json=payload)
    assert resp.status_code == 200
    assert resp.json()["result"].get("skipped") is True


async def test_registry_and_ubo_read_cosmos_records(monkeypatch):
    class FakeContainer:
        def query_items(self, query=None, parameters=None, enable_cross_partition_query=False):
            return [
                {
                    "name": "Acme",
                    "incorporated_date": "2020-01-01",
                    "ownership_percentage": 60,
                    "entity_type": "individual",
                    "jurisdiction": "GB",
                }
            ]

    class FakeDB:
        def get_container_client(self, name):
            return FakeContainer()

    monkeypatch.setattr(reg, "get_cosmos_database", lambda: FakeDB())
    monkeypatch.setattr(ubo, "get_cosmos_database", lambda: FakeDB())

    assert (await reg.registry_lookup("Acme", None))["found"] is True
    assert (await ubo.ubo_resolver("Acme", {}))["ubos"]


async def test_registry_and_ubo_fall_back_to_mock_without_cosmos(monkeypatch):
    def no_db():
        raise RuntimeError("no db")

    monkeypatch.setattr(reg, "get_cosmos_database", no_db)
    monkeypatch.setattr(ubo, "get_cosmos_database", no_db)

    assert (await reg.registry_lookup("Acme", None))["source"] == "mock"
    assert (await ubo.ubo_resolver("Acme", {}))["source"] == "mock"
