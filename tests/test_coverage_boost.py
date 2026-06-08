import asyncio
import base64
import types
import pytest

from agents.orchestrator import agent as orchestrator


@pytest.mark.asyncio
async def test_synthesise_report_handles_missing_and_present_fields():
    # compliance with result keys
    comp = {"status": "ok", "result": {"risk_summary": {"tier": "HIGH"}, "explanation": "Found risks", "foundry_iq_queries": 2}}
    identity = {"status": "ok"}
    screening = {"status": "ok", "result": {"foundry_iq_queries": 1}}
    corporate = {"status": "ok"}
    transaction = {"status": "ok"}

    rpt = await orchestrator.synthesise_report("tid", {"entity_name": "Acme"}, identity, screening, corporate, transaction, comp)
    assert rpt["report_id"].startswith("argus-rpt-")
    assert rpt["entity"]["name"] == "Acme"
    assert rpt["risk_summary"]["tier"] == "HIGH"
    # foundry_iq_queries aggregated
    assert rpt["audit_trace"]["foundry_iq_queries"] == 3


@pytest.mark.asyncio
async def test_run_kyc_assessment_with_mocked_call_agent(monkeypatch):
    # Patch call_agent to return simple structured results for each agent
    async def fake_call(agent_name, payload, task_id):
        return {"agent": agent_name, "status": "ok", "result": {"foo": agent_name}}

    monkeypatch.setattr(orchestrator, "call_agent", fake_call)

    kyc = {"entity_name": "TestCo", "entity_type": "company", "jurisdiction": "NL"}
    report = await orchestrator.run_kyc_assessment(kyc)
    assert report["entity"]["name"] == "TestCo"
    assert "audit_trace" in report
    assert report["audit_trace"]["agents_invoked"] == ["identity", "screening", "corporate", "transaction", "compliance"]


def test_regulations_helpers_and_normalize():
    import agents.compliance.tools.regulations_rag as rr

    assert rr._normalize_relevance(0.5) == 0.5
    assert rr._normalize_relevance(2.0) == 0.5


@pytest.mark.asyncio
async def test_regulations_rag_returns_mock(monkeypatch):
    from agents.compliance.tools import regulations_rag as rr

    # Force Foundry client errors by patching get_foundry_client in the module
    import agents.compliance.tools.regulations_rag as mod

    monkeypatch.setattr(mod, "get_foundry_client", lambda: (_ for _ in ()).throw(RuntimeError("no client")))

    res = await rr.regulations_rag("Q", "NL", "company", ["fraud"])
    assert res["source"] == "mock"


@pytest.mark.asyncio
async def test_regulations_and_adverse_positive(monkeypatch):
    # positive branch: fake foundry client returns items
    import agents.compliance.tools.regulations_rag as rrmod

    class FakeKB:
        def query(self, knowledge_base_name=None, query=None, top=0, include_citations=False):
            return {"items": [{"relevance_score": 0.5, "content": "Some rule text", "citation": {"document_title": "doc.pdf", "section": "sec1", "snippet_id": "s1"}, "id": "i1"}]}

    class FakeClient:
        knowledge_bases = FakeKB()

    monkeypatch.setattr(rrmod, "get_foundry_client", lambda: FakeClient())
    res = await rrmod.regulations_rag("Q", "NL", "company", ["fraud"])
    assert res["source"] == "foundry_iq"
    assert res["regulations"]


@pytest.mark.asyncio
async def test_adverse_and_sanctions_positive(monkeypatch):
    import agents.screening.tools.adverse_media_scanner as am
    import agents.screening.tools.sanctions_checker as sc

    class FakeKB:
        def query(self, knowledge_base_name=None, query=None, top=0, include_citations=False):
            return {"items": [{"relevance_score": 0.6, "content": "bad news about X", "citation": {"document_title": "news.pdf", "snippet_id": "nid"}, "metadata_json": '{"published_at": "2025-01-01", "tags": ["fraud"]}', "id": "x1"}]}

    class FakeClient:
        knowledge_bases = FakeKB()

    monkeypatch.setattr(am, "get_foundry_client", lambda: FakeClient())
    monkeypatch.setattr(sc, "get_foundry_client", lambda: FakeClient())

    ares = await am.adverse_media_scanner("X", ["X"])
    assert ares["hit"] is True

    sres = await sc.sanctions_checker("X", ["X"], "NL")
    assert sres["hit"] is True


@pytest.mark.asyncio
async def test_registry_customer_and_ubo_with_db(monkeypatch):
    import agents.corporate.tools.registry_lookup as reg
    import agents.identity.tools.customer_lookup as cust
    import agents.corporate.tools.ubo_resolver as ubo

    class FakeContainer:
        def query_items(self, query=None, parameters=None, enable_cross_partition_query=False):
            return [{"name": "Acme", "incorporated_date": "2020-01-01", "ownership_percentage": 60, "entity_type": "individual", "jurisdiction": "GB"}]

    class FakeDB:
        def get_container_client(self, name):
            return FakeContainer()

    monkeypatch.setattr(reg, "get_cosmos_database", lambda: FakeDB())
    monkeypatch.setattr(cust, "get_cosmos_database", lambda: FakeDB())
    monkeypatch.setattr(ubo, "get_cosmos_database", lambda: FakeDB())

    r = await reg.registry_lookup("Acme", None)
    assert r["found"] is True

    c = await cust.customer_lookup("Acme", "company", None)
    assert c["found"] is True

    u = await ubo.ubo_resolver("Acme", {})
    assert u["ubos"]


@pytest.mark.asyncio
async def test_corporate_agent_invoke(monkeypatch):
    import agents.corporate.agent as corp

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

    msg = corp.A2AMessage(a2a_version="1.0", source_agent="x", target_agent="y", task_id="t1", payload={"entity_name": "Acme", "entity_type": "corporate", "jurisdiction": "GB"})
    res = await corp.invoke(msg)
    assert res["result"]["corporate_score"] <= 100


@pytest.mark.asyncio
async def test_identity_agent_invoke(monkeypatch):
    import agents.identity.agent as ident

    monkeypatch.setattr(ident, "get_demo_profile", lambda name, etype, j: None)
    async def fake_customer(name, etype, rn):
        return {"found": True}
    async def fake_ocr(img, dt):
        return {"fields": {}, "confidence": 0.9}
    async def fake_validator(reg, ocr):
        return {"confidence_score": 88, "verified_fields": []}
    monkeypatch.setattr(ident, "customer_lookup", fake_customer)
    monkeypatch.setattr(ident, "ocr_processor", fake_ocr)
    monkeypatch.setattr(ident, "identity_validator", fake_validator)

    msg = ident.A2AMessage(a2a_version="1.0", source_agent="x", target_agent="y", task_id="t2", payload={"entity_name": "Bob", "entity_type": "individual", "documents": []})
    res = await ident.invoke(msg)
    assert res["result"]["identity_score"] >= 0


@pytest.mark.asyncio
async def test_compliance_agent_invoke(monkeypatch):
    import agents.compliance.agent as comp

    # Patch external tool calls
    async def fake_reg(q, j, t, ri):
        return {"regulations": []}
    monkeypatch.setattr(comp, "regulations_rag", fake_reg)
    monkeypatch.setattr(comp, "risk_scorer", lambda i, s, c, t: {"overall": 60, "dimensions": {}, "confidence": 0.85})
    monkeypatch.setattr(comp, "gap_analyzer", lambda ri, regs, scores: ["gap1"]) 
    async def fake_explain(*args, **kwargs):
        return "explanation"
    monkeypatch.setattr(comp, "explain_decision", fake_explain)

    payload = {
        "entity_name": "Z",
        "entity_type": "company",
        "jurisdiction": "GB",
        "upstream_results": {
            "identity": {"result": {}},
            "screening": {"result": {"pep_hit": True, "findings": [{"type":"pep","match":"John"}]}},
            "corporate": {"result": {"risk_flags": []}},
            "transaction": {"result": {}},
        }
    }
    msg = comp.A2AMessage(a2a_version="1.0", source_agent="x", target_agent="y", task_id="t3", payload=payload)
    res = await comp.invoke(msg)
    assert res["result"]["risk_summary"]["overall_risk_tier"] == "HIGH"


@pytest.mark.asyncio
async def test_registry_and_customer_and_ubo_mock(monkeypatch):
    import agents.corporate.tools.registry_lookup as reg
    import agents.identity.tools.customer_lookup as cust
    import agents.corporate.tools.ubo_resolver as ubo

    # Patch get_cosmos_database in each module to raise, hitting mock branches
    monkeypatch.setattr(reg, "get_cosmos_database", lambda: (_ for _ in ()).throw(RuntimeError("no db")))
    monkeypatch.setattr(cust, "get_cosmos_database", lambda: (_ for _ in ()).throw(RuntimeError("no db")))
    monkeypatch.setattr(ubo, "get_cosmos_database", lambda: (_ for _ in ()).throw(RuntimeError("no db")))

    r = await reg.registry_lookup("Acme", None)
    assert r.get("source") == "mock"

    c = await cust.customer_lookup("Acme", "company", None)
    assert c.get("found") is True

    u = await ubo.ubo_resolver("Acme", {})
    assert u.get("source") == "mock"


@pytest.mark.asyncio
async def test_screening_tools_mock_and_metadata(monkeypatch):
    import agents.screening.tools.adverse_media_scanner as am
    import agents.screening.tools.sanctions_checker as sc

    # Patch get_foundry_client to raise
    monkeypatch.setattr(am, "get_foundry_client", lambda: (_ for _ in ()).throw(RuntimeError("no client")))
    monkeypatch.setattr(sc, "get_foundry_client", lambda: (_ for _ in ()).throw(RuntimeError("no client")))

    r = await am.adverse_media_scanner("Alice", ["A"])
    assert r["source"] == "mock"

    s = await sc.sanctions_checker("Alice", ["A"], "NL")
    assert s["source"] == "mock"


@pytest.mark.asyncio
async def test_typology_and_transaction_monitor_and_ocr():
    from agents.transaction.tools import typology_matcher, transaction_monitor
    from agents.identity.tools import ocr_processor

    # typology: empty patterns -> []
    assert await typology_matcher.typology_matcher({}) == []

    # typology with structuring -> mock hits
    hits = await typology_matcher.typology_matcher({"structuring_flag": True})
    assert isinstance(hits, list) and hits

    # force DB error path for transaction monitor to get mock
    import agents.transaction.tools.transaction_monitor as tm
    import pytest
    # monkeypatch the get_cosmos_database used inside module
    from pytest import MonkeyPatch
    mp = MonkeyPatch()
    mp.setattr(tm, "get_cosmos_database", lambda: (_ for _ in ()).throw(RuntimeError("no db")))
    try:
        tx = await transaction_monitor.transaction_monitor("Someone")
        assert tx.get("source") == "mock"
    finally:
        mp.undo()

    # ocr_processor: empty image -> error result
    res = await ocr_processor.ocr_processor("", "passport")
    assert res.get("error")


# ── pep_checker: DB hit ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pep_checker_db_hit(monkeypatch):
    import agents.screening.tools.pep_checker as pc

    class FakeContainer:
        def query_items(self, query=None, parameters=None, enable_cross_partition_query=False):
            return [{"name": "John Doe", "role": "Minister", "country": "DE", "period": "2020-2024"}]

    class FakeDB:
        def get_container_client(self, name):
            return FakeContainer()

    monkeypatch.setattr(pc, "get_cosmos_database", lambda: FakeDB())
    result = await pc.pep_checker("John Doe", "1970-01-01", "DE")
    assert result["hit"] is True
    assert result["findings"][0]["type"] == "pep"
    assert "Minister" in result["findings"][0]["match"]


@pytest.mark.asyncio
async def test_pep_checker_db_no_hit(monkeypatch):
    import agents.screening.tools.pep_checker as pc

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


# ── transaction_monitor: DB hit + empty ──────────────────────────────────────
@pytest.mark.asyncio
async def test_transaction_monitor_db_hit(monkeypatch):
    import agents.transaction.tools.transaction_monitor as tm

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


@pytest.mark.asyncio
async def test_transaction_monitor_db_empty(monkeypatch):
    import agents.transaction.tools.transaction_monitor as tm

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


# ── typology_matcher: search-client positive hits ────────────────────────────
@pytest.mark.asyncio
async def test_typology_matcher_search_hit(monkeypatch):
    import agents.transaction.tools.typology_matcher as tmt

    class FakeResult:
        def __init__(self, hits):
            self._hits = hits

        def __iter__(self):
            return iter(self._hits)

    class FakeClient:
        def search(self, search_text=None, top=None):
            return FakeResult([
                {"typology_name": "Smurfing", "description": "Cash structuring below threshold",
                 "fatf_reference": "FATF-2023-3.2", "@search.score": 0.95}
            ])

    monkeypatch.setattr(tmt, "get_search_client", lambda index: FakeClient())
    hits = await tmt.typology_matcher({"structuring_flag": True})
    assert hits
    assert hits[0]["typology"] == "Smurfing"


@pytest.mark.asyncio
async def test_typology_matcher_regulations_fallback(monkeypatch):
    import agents.transaction.tools.typology_matcher as tmt

    call_count = 0

    class EmptyResult:
        def __iter__(self):
            return iter([])

    class RegResult:
        def __iter__(self):
            return iter([
                {"title": "Layering typology", "content": "Multi-hop rapid movement",
                 "source_doc": "FATF-4.1", "@search.score": 0.88}
            ])

    class FakeClient:
        def search(self, search_text=None, top=None):
            nonlocal call_count
            call_count += 1
            return EmptyResult() if call_count == 1 else RegResult()

    monkeypatch.setattr(tmt, "get_search_client", lambda index: FakeClient())
    hits = await tmt.typology_matcher({"layering_flag": True})
    assert hits
    assert "typology" in hits[0]


# ── ocr_processor: mock fallback for all doc types ───────────────────────────
@pytest.mark.asyncio
async def test_ocr_processor_mock_all_doc_types(monkeypatch):
    from agents.identity.tools import ocr_processor as ocp
    import base64

    # Force the Azure import to fail so we exercise _mock_ocr for each doc type
    monkeypatch.setenv("DOC_INTELLIGENCE_ENDPOINT", "")
    monkeypatch.setenv("DOC_INTELLIGENCE_KEY", "")

    fake_b64 = base64.b64encode(b"fake-image-bytes").decode()

    for doc_type in ("passport", "drivers_license", "id_card", "tax_invoice"):
        result = await ocp.ocr_processor(fake_b64, doc_type)
        assert result["doc_type"] == doc_type
        assert result["fields"]
        assert result["confidence"] > 0


# ── orchestrator: call_agent HTTP error path ─────────────────────────────────
@pytest.mark.asyncio
async def test_call_agent_http_error(monkeypatch):
    import httpx
    from agents.orchestrator import agent as orch

    async def raise_http(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    # Monkeypatch httpx.AsyncClient.post
    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeAsyncClient())
    result = await orch.call_agent("identity", {"entity_name": "X"}, "task-err-001")
    assert result["status"] == "error"
    assert result["agent"] == "identity"
