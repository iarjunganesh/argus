"""Corporate agent scoring and its registry and ownership tools."""

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


async def test_registry_lookup_reports_missing_entity():
    assert await reg.registry_lookup("Unknown Ltd", None) == {
        "found": False,
        "record": None,
        "source": "local",
    }


async def test_ubo_resolver_recurses_through_corporate_owners():
    result = await ubo.ubo_resolver("Harbor Test Holdings", {})

    assert [u["name"] for u in result["ubos"]] == ["Pat Politico", "Ada Synthetic"]
    assert result["ubos"][0]["depth"] == 2
    assert [n["name"] for n in result["ownership_chain"]] == [
        "Offshore Test SPC",
        "Pat Politico",
        "Ada Synthetic",
        "Minor Holder",  # in the chain, but 5% is below the ownership threshold
    ]
    assert result["source"] == "local"


async def test_ubo_resolver_marks_a_fallback_deeper_in_the_chain(use_plane):
    from argus.data_plane import DataPlaneUnavailable

    class Graph:
        async def ownership_children(self, name):
            if name == "Parent":
                return [{"name": "Sub", "entity_type": "corporate", "ownership_percentage": 100}]
            raise DataPlaneUnavailable("down")

    use_plane(entities=Graph())
    result = await ubo.ubo_resolver("Parent", {})

    assert result["source"] == "fallback"
    assert [n["name"] for n in result["ownership_chain"]] == ["Sub"]


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


async def test_registry_lookup_reads_the_local_registry():
    result = await reg.registry_lookup("Harbor Test Holdings", None)

    assert result["found"] is True and result["record"]["entity_id"] == "CORP-T0001"


async def test_registry_and_ubo_fall_back_when_the_store_is_down(use_plane, unavailable):
    use_plane(entities=unavailable)

    assert (await reg.registry_lookup("Acme", None))["source"] == "fallback"
    assert (await ubo.ubo_resolver("Acme", {}))["source"] == "fallback"


async def test_agent_reports_its_provenance(use_plane, unavailable):
    payload = {"entity_name": "Harbor Test Holdings", "entity_type": "corporate"}
    response = await corp.invoke(_msg({**payload, "jurisdiction": "KY"}))
    assert response["source"] == "computed"
    assert response["result"]["risk_flags"] == [
        "High-risk jurisdiction node: Offshore Test SPC (PA)"
    ]

    use_plane(entities=unavailable)
    response = await corp.invoke(_msg({**payload, "jurisdiction": "KY"}))
    assert response["fallbacks"] == ["registry_lookup", "ubo_resolver"]
