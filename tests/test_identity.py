"""Identity agent flow and the registry/document cross-check."""

import base64

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


async def test_customer_lookup_reports_missing_entity():
    assert await cust.customer_lookup("Nobody", "individual", None) == {
        "found": False,
        "record": None,
        "source": "local",
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


async def test_ocr_without_an_engine_reads_nothing_and_says_so():
    from argus.agents.identity.tools import ocr_processor as ocp

    fake_b64 = base64.b64encode(b"fake-image-bytes").decode()
    result = await ocp.ocr_processor(fake_b64, "passport")

    assert result == {"doc_type": "passport", "fields": {}, "confidence": 0.0, "source": "fallback"}


async def test_ocr_reports_the_lowest_field_confidence(use_plane):
    from argus.agents.identity.tools.ocr_processor import ocr_processor

    class OCR:
        async def extract(self, image, doc_type):
            assert image == b"Hello"
            return {"full_name": {"value": "Jane", "confidence": 0.9}, "x": {"confidence": 0.7}}

    use_plane(ocr=OCR())
    result = await ocr_processor("SGVsbG8=", "passport")

    assert result["confidence"] == 0.7 and result["source"] == "local"


async def test_ocr_rejects_text_that_is_not_base64():
    from argus.agents.identity.tools.ocr_processor import ocr_processor

    assert (await ocr_processor("not base64!", "passport"))["error"] == "Not base64"


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


def test_openapi_docs_are_served():
    from argus.agents.identity.agent import app

    client = TestClient(app)
    resp = client.get("/docs")
    assert resp.status_code == 200


async def test_customer_lookup_reads_the_local_registry():
    result = await cust.customer_lookup("Ada Synthetic", "individual", None)

    assert result["found"] is True and result["record"]["entity_id"] == "IND-T0001"


async def test_customer_lookup_falls_back_when_the_store_is_down(use_plane, unavailable):
    use_plane(entities=unavailable)

    result = await cust.customer_lookup("Acme", "corporate", None)

    assert result == {"found": False, "record": None, "source": "fallback"}


async def test_agent_names_the_tools_that_fell_back():
    payload = {
        "entity_name": "Ada Synthetic",
        "entity_type": "individual",
        "documents": [{"image_base64": base64.b64encode(b"x").decode()}],
    }
    response = await ident.invoke(_msg(payload))

    assert response["source"] == "fallback"
    assert response["fallbacks"] == ["ocr_processor[0]"]
    assert response["result"]["registry_match"] is True


async def test_demo_profile_is_labelled():
    payload = {"entity_name": "Jane Synthetic", "entity_type": "individual", "jurisdiction": "DE"}

    assert (await ident.invoke(_msg(payload)))["source"] == "demo_profile"


async def test_ocr_processor_rejects_an_empty_image():
    from argus.agents.identity.tools import ocr_processor

    assert (await ocr_processor.ocr_processor("", "passport")).get("error")
