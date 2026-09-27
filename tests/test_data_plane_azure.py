"""The Azure data plane against stand-ins for the Azure SDKs: requests out, results back."""

from types import SimpleNamespace

import pytest

import argus.data_plane.azure as az
from argus.data_plane import DataPlaneUnavailable

# ── AI Search ─────────────────────────────────────────────────────────────────


class SearchClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return iter(self.rows)


async def test_search_uses_the_semantic_ranker_and_normalises_scores(monkeypatch):
    client = SearchClient(
        [
            {
                "id": "a",
                "title": "T",
                "content": "C",
                "source_doc": "doc.pdf",
                "@search.reranker_score": 3.0,
                "metadata_json": '{"program": "EU"}',
            },
            {"id": "b", "@search.score": 7.5, "metadata_json": "{not json"},
        ]
    )
    indexes = []
    monkeypatch.setattr(az, "get_search_client", lambda name: indexes.append(name) or client)

    first, second = await az.AzureSearchRetriever().search("sanctions", "Viktor", top=3)

    assert indexes == ["argus-kb-sanctions"]
    assert client.calls == [
        {
            "search_text": "Viktor",
            "top": 3,
            "query_type": "semantic",
            "semantic_configuration_name": "default",
        }
    ]
    assert (first.score, first.metadata, first.source_doc) == (0.75, {"program": "EU"}, "doc.pdf")
    assert (second.score, second.metadata, second.title) == (1.0, {}, "")


async def test_any_search_failure_is_reported_as_unavailable(monkeypatch):
    def broken(name):
        raise RuntimeError("AZURE_SEARCH_ENDPOINT is not set")

    monkeypatch.setattr(az, "get_search_client", broken)

    with pytest.raises(DataPlaneUnavailable, match="AI Search regulations"):
        await az.AzureSearchRetriever().search("regulations", "q")


# ── Cosmos DB ─────────────────────────────────────────────────────────────────


class Container:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.queries = []
        self.upserts = []

    def query_items(self, query, parameters, enable_cross_partition_query):
        self.queries.append((query, parameters))
        return self.rows

    def upsert_item(self, item):
        self.upserts.append(item)
        self.rows = [item]


class Database:
    def __init__(self, container):
        self.container = container
        self.names = []

    def get_container_client(self, name):
        self.names.append(name)
        return self.container


def _cosmos(monkeypatch, rows=()):
    db = Database(Container(rows))
    monkeypatch.setattr(az, "get_cosmos_database", lambda: db)
    return db


async def test_entity_queries_use_the_right_containers(monkeypatch):
    db = _cosmos(monkeypatch, [{"name": "Acme"}])
    store = az.CosmosEntityStore()

    assert await store.find_entity("Acme", "corporate") == {"name": "Acme"}
    assert await store.find_entity("Acme") == {"name": "Acme"}
    assert await store.find_pep("Acme") == {"name": "Acme"}
    assert await store.ownership_children("Acme") == [{"name": "Acme"}]
    assert await store.transactions("Acme", limit=7) == [{"name": "Acme"}]

    assert db.names == ["entities", "entities", "entities", "corporate_graph", "transactions"]
    typed, untyped, pep, _, transactions = db.container.queries
    assert typed[1] == [{"name": "@name", "value": "Acme"}, {"name": "@type", "value": "corporate"}]
    assert "entity_type" not in untyped[0]
    assert "is_pep = true" in pep[0]
    assert "LIMIT @limit" in transactions[0]  # every value is a parameter, none is formatted in
    assert {"name": "@limit", "value": 7} in transactions[1]


async def test_entity_lookups_without_matches(monkeypatch):
    _cosmos(monkeypatch)
    store = az.CosmosEntityStore()

    assert await store.find_entity("Nobody") is None
    assert await store.find_pep("Nobody") is None


async def test_cosmos_failure_is_reported_as_unavailable(monkeypatch):
    def broken():
        raise RuntimeError("COSMOS_ENDPOINT is not set")

    monkeypatch.setattr(az, "get_cosmos_database", broken)

    with pytest.raises(DataPlaneUnavailable, match="Cosmos entities"):
        await az.CosmosEntityStore().find_entity("Acme")


async def test_report_store_keeps_status_and_report_in_one_document(monkeypatch):
    db = _cosmos(monkeypatch)
    store = az.CosmosReportStore()

    assert await store.status("r1") is None and await store.report("r1") is None
    await store.save_status("r1", "processing")
    await store.save_report("r1", {"tier": "LOW"})

    assert db.container.upserts[-1] == {
        "id": "r1",
        "report_id": "r1",
        "status": "processing",
        "report": {"tier": "LOW"},
    }
    assert await store.status("r1") == "processing"
    assert await store.report("r1") == {"tier": "LOW"}


async def test_report_store_appends_progress_events_to_the_report_document(monkeypatch):
    db = _cosmos(monkeypatch)
    store = az.CosmosReportStore()

    assert await store.events("r1") == []
    await store.save_status("r1", "processing")
    await store.append_event("r1", {"type": "agent_started"})
    await store.append_event("r1", {"type": "agent_completed"})

    assert db.container.upserts[-1] == {
        "id": "r1",
        "report_id": "r1",
        "status": "processing",
        "events": [{"type": "agent_started"}, {"type": "agent_completed"}],
    }
    assert await store.events("r1") == [{"type": "agent_started"}, {"type": "agent_completed"}]


# ── Document Intelligence ─────────────────────────────────────────────────────


def _field(content, confidence):
    return SimpleNamespace(content=content, confidence=confidence)


def test_id_fields_are_mapped_to_argus_names():
    result = SimpleNamespace(
        documents=[
            SimpleNamespace(
                fields={
                    "FirstName": _field("Jane", 0.9),
                    "LastName": _field("Doe", 0.8),
                    "DateOfBirth": _field("1980-01-15", 0.95),
                    "Unmapped": _field("x", 0.1),
                }
            ),
            SimpleNamespace(fields=None),
        ]
    )

    assert az._id_fields(result) == {
        "full_name": {"value": "Jane Doe", "confidence": 0.8},
        "date_of_birth": {"value": "1980-01-15", "confidence": 0.95},
    }
    assert az._id_fields(SimpleNamespace(documents=None)) == {}


async def test_ocr_sends_the_image_to_the_id_model(monkeypatch):
    sent = {}

    class Client:
        def __init__(self, endpoint, credential):
            sent["endpoint"], sent["key"] = endpoint, credential.key

        def begin_analyze_document(self, model_id, request):
            sent["model"], sent["bytes"] = model_id, request.bytes_source
            document = SimpleNamespace(fields={"LastName": _field("Doe", 0.7)})
            return SimpleNamespace(result=lambda: SimpleNamespace(documents=[document]))

    monkeypatch.setattr("azure.ai.documentintelligence.DocumentIntelligenceClient", Client)
    monkeypatch.setenv("DOC_INTELLIGENCE_ENDPOINT", "https://di.example")
    monkeypatch.setenv("DOC_INTELLIGENCE_KEY", "di-test")

    fields = await az.DocumentIntelligenceOCR().extract(b"img", "passport")

    assert fields == {"full_name": {"value": "Doe", "confidence": 0.7}}
    assert sent == {
        "endpoint": "https://di.example",
        "key": "di-test",
        "model": "prebuilt-idDocument",
        "bytes": b"img",
    }


async def test_ocr_without_settings_is_unavailable():
    with pytest.raises(DataPlaneUnavailable, match="Document Intelligence"):
        await az.DocumentIntelligenceOCR().extract(b"img", "passport")


def test_every_cosmos_container_is_partitioned_on_a_field_its_records_have():
    """`infra/create_cosmos_db.py` partition keys match what `upload_to_cosmos.py` uploads."""
    import ast
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "infra" / "create_cosmos_db.py").read_text(encoding="utf-8"))
    containers = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "CONTAINERS"
    )
    keys = {c["id"]: c["partition_key"].lstrip("/") for c in containers}
    synthetic = root / "tests" / "fixtures" / "data" / "synthetic"
    for container in ("entities", "corporate_graph", "transactions"):
        lines = (synthetic / f"{container}.jsonl").read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        assert records and all(keys[container] in r for r in records), container
