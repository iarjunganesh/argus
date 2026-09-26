"""Identity agent flow and the registry/document cross-check."""

import base64
import sys
import types

from fastapi.testclient import TestClient

import argus.agents.identity.agent as ident
import argus.agents.identity.tools.customer_lookup as cust
from argus.agents.identity.tools.identity_validator import identity_validator


def _msg(payload: dict) -> ident.A2AMessage:
    return ident.A2AMessage(
        a2a_version="1.0",
        source_agent="test",
        target_agent="identity",
        task_id="t-id",
        payload=payload,
    )


async def test_each_document_is_read_and_cross_checked(monkeypatch):
    read = []

    async def lookup(name, entity_type, number):
        return {"found": True, "record": {"name": "Jan Test"}}

    async def ocr(image, doc_type):
        read.append((image, doc_type))
        return {"fields": {"full_name": {"value": "Jan Test"}}}

    monkeypatch.setattr(ident, "customer_lookup", lookup)
    monkeypatch.setattr(ident, "ocr_processor", ocr)

    payload = {
        "entity_name": "Jan Test",
        "documents": [{"image_base64": "AAA", "doc_type": "id_card"}, {}],
    }
    result = (await ident.invoke(_msg(payload)))["result"]

    assert read == [("AAA", "id_card"), ("", "passport")]
    assert result["ocr_documents"] == 2
    assert result["verified_fields"] == ["name", "name"]
    assert result["identity_score"] == 100


async def test_demo_profile_short_circuits_the_tools():
    payload = {"entity_name": "Jane Synthetic", "entity_type": "individual", "jurisdiction": "DE"}
    response = await ident.invoke(_msg(payload))

    assert response["result"]["identity_score"] == 96


def test_health():
    assert TestClient(ident.app).get("/health").json()["service"] == "identity"


async def test_customer_lookup_reports_missing_entity(monkeypatch):
    class DB:
        def get_container_client(self, name):
            class Container:
                def query_items(self, **kwargs):
                    return []

            return Container()

    monkeypatch.setattr(cust, "get_cosmos_database", DB)

    assert await cust.customer_lookup("Nobody", "individual", None) == {
        "found": False,
        "record": None,
    }


async def test_date_of_birth_checked_even_without_registry_name():
    registry = {"record": {"date_of_birth": "1990-01-01"}}
    documents = [
        {"fields": {"full_name": {"value": "A"}, "date_of_birth": {"value": "1990-01-01"}}},
        {"fields": {"date_of_birth": {"value": "1991-02-02"}}},
    ]

    result = await identity_validator(registry, documents)

    assert result["verified_fields"] == ["date_of_birth"]
    assert result["discrepancies"] == [
        {
            "field": "date_of_birth",
            "registry": "1990-01-01",
            "document": "1991-02-02",
            "severity": "medium",
        }
    ]
    assert result["confidence_score"] == 90


async def test_identity_agent_invoke(monkeypatch):
    import argus.agents.identity.agent as ident

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

    msg = ident.A2AMessage(
        a2a_version="1.0",
        source_agent="x",
        target_agent="y",
        task_id="t2",
        payload={"entity_name": "Bob", "entity_type": "individual", "documents": []},
    )
    res = await ident.invoke(msg)
    assert res["result"]["identity_score"] >= 0


async def test_ocr_processor_mock_all_doc_types(monkeypatch):
    from argus.agents.identity.tools import ocr_processor as ocp

    # Force the Azure import to fail so we exercise _mock_ocr for each doc type
    monkeypatch.setenv("DOC_INTELLIGENCE_ENDPOINT", "")
    monkeypatch.setenv("DOC_INTELLIGENCE_KEY", "")

    fake_b64 = base64.b64encode(b"fake-image-bytes").decode()

    for doc_type in ("passport", "drivers_license", "id_card", "tax_invoice"):
        result = await ocp.ocr_processor(fake_b64, doc_type)
        assert result["doc_type"] == doc_type
        assert result["fields"]
        assert result["confidence"] > 0


async def test_identity_validator_name_match():
    from argus.agents.identity.tools.identity_validator import identity_validator

    registry = {"found": True, "record": {"name": "Jane Doe", "date_of_birth": "1980-01-15"}}
    ocr = [
        {"fields": {"full_name": {"value": "Jane Doe"}, "date_of_birth": {"value": "1980-01-15"}}}
    ]
    result = await identity_validator(registry, ocr)
    assert "name" in result["verified_fields"]
    assert result["confidence_score"] == 100


async def test_identity_validator_name_mismatch():
    from argus.agents.identity.tools.identity_validator import identity_validator

    registry = {"found": True, "record": {"name": "Jane Doe"}}
    ocr = [{"fields": {"full_name": {"value": "John Smith"}}}]
    result = await identity_validator(registry, ocr)
    assert len(result["discrepancies"]) == 1
    assert result["discrepancies"][0]["field"] == "name"
    assert result["confidence_score"] < 100


async def test_ocr_processor_azure_doc_intelligence_success(monkeypatch):
    from argus.agents.identity.tools.ocr_processor import ocr_processor

    class FakeField:
        def __init__(self, value, confidence):
            self.value = value
            self.confidence = confidence

    class FakeDoc:
        def __init__(self):
            self.fields = {
                "full_name": FakeField("Jane Doe", 0.99),
                "passport_number": FakeField("P123", 0.98),
            }

    class FakeResult:
        def __init__(self):
            self.documents = [FakeDoc()]

    class FakePoller:
        def result(self):
            return FakeResult()

    class FakeDocumentAnalysisClient:
        def __init__(self, endpoint=None, credential=None):
            self.endpoint = endpoint
            self.credential = credential

        def begin_analyze_document(self, model_id, document=None):
            return FakePoller()

    class FakeAzureKeyCredential:
        def __init__(self, key):
            self.key = key

    # Inject minimal Azure SDK module tree expected by ocr_processor.
    azure_mod = types.ModuleType("azure")
    ai_mod = types.ModuleType("azure.ai")
    form_mod = types.ModuleType("azure.ai.formrecognizer")
    core_mod = types.ModuleType("azure.core")
    cred_mod = types.ModuleType("azure.core.credentials")
    form_mod.DocumentAnalysisClient = FakeDocumentAnalysisClient
    cred_mod.AzureKeyCredential = FakeAzureKeyCredential

    monkeypatch.setitem(sys.modules, "azure", azure_mod)
    monkeypatch.setitem(sys.modules, "azure.ai", ai_mod)
    monkeypatch.setitem(sys.modules, "azure.ai.formrecognizer", form_mod)
    monkeypatch.setitem(sys.modules, "azure.core", core_mod)
    monkeypatch.setitem(sys.modules, "azure.core.credentials", cred_mod)

    monkeypatch.setenv("DOC_INTELLIGENCE_ENDPOINT", "https://example.cognitiveservices.azure.com")
    monkeypatch.setenv("DOC_INTELLIGENCE_KEY", "fake-key")

    result = await ocr_processor("SGVsbG8=", "passport")
    assert result["source"] == "azure_doc_intelligence"
    assert result["fields"]["full_name"]["value"] == "Jane Doe"


def test_openapi_docs_are_served():
    from argus.agents.identity.agent import app

    client = TestClient(app)
    resp = client.get("/docs")
    assert resp.status_code == 200


async def test_customer_lookup_reads_cosmos_record(monkeypatch):
    class Container:
        def query_items(self, **kwargs):
            return [{"name": "Acme"}]

    class DB:
        def get_container_client(self, name):
            return Container()

    monkeypatch.setattr(cust, "get_cosmos_database", DB)

    assert (await cust.customer_lookup("Acme", "corporate", None))["found"] is True


async def test_customer_lookup_falls_back_to_mock_without_cosmos(monkeypatch):
    def no_db():
        raise RuntimeError("no db")

    monkeypatch.setattr(cust, "get_cosmos_database", no_db)

    result = await cust.customer_lookup("Acme", "corporate", None)
    assert result["found"] is True
    assert result["record"]["entity_id"] == "MOCK-001"


async def test_ocr_processor_rejects_an_empty_image():
    from argus.agents.identity.tools import ocr_processor

    assert (await ocr_processor.ocr_processor("", "passport")).get("error")
