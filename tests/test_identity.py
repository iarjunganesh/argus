"""Identity agent flow and the registry/document cross-check."""

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
