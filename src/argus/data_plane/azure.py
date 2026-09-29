"""Azure data plane: Foundry IQ knowledge bases on AI Search, Cosmos DB and Document Intelligence.

Each call runs the synchronous Azure SDK in a worker thread. Any failure (missing settings,
network, service errors) becomes `DataPlaneUnavailable`, so the calling tool falls back and says so.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from typing import Any

from argus.config import (
    get_cosmos_database,
    get_document_intelligence_client,
    get_knowledge_base_client,
)
from argus.data_plane.base import DataPlaneUnavailable, KnowledgeBase, Passage

# Each knowledge base reads one search index through one knowledge source. The knowledge base
# and its index share a name; `infra/foundry_iq/create_knowledge_bases.py` creates all three.
KNOWLEDGE_BASE_NAMES: dict[KnowledgeBase, str] = {
    "regulations": os.getenv("FOUNDRY_IQ_KB_REGULATIONS", "argus-kb-regulations"),
    "sanctions": os.getenv("FOUNDRY_IQ_KB_SANCTIONS", "argus-kb-sanctions"),
    "adverse_media": os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA", "argus-kb-adversemedia"),
}


def knowledge_source_name(knowledge_base: KnowledgeBase) -> str:
    return f"{KNOWLEDGE_BASE_NAMES[knowledge_base]}-source"


# The index fields a knowledge source returns with each reference: everything a Passage needs.
SOURCE_DATA_FIELDS = ("id", "title", "content", "source_doc", "metadata_json")

REPORTS_CONTAINER = "kyc_reports"
_RERANKER_MAX = 4.0  # semantic ranker scores run from 0 to 4


async def _call[T](what: str, fn: Callable[[], T]) -> T:
    try:
        return await asyncio.to_thread(fn)
    except Exception as exc:  # any SDK, auth or network failure means the service is unavailable
        raise DataPlaneUnavailable(f"{what}: {exc}") from exc


class FoundryIQRetriever:
    """Searches a Foundry IQ knowledge base with the retrieve action.

    The stable API (2026-04-01) runs the query as a semantic intent, without a model: retrieval is
    minimal and extractive, and each reference carries the index fields in SOURCE_DATA_FIELDS and
    its semantic reranker score.
    """

    async def search(
        self, knowledge_base: KnowledgeBase, query: str, top: int = 5
    ) -> list[Passage]:
        def run() -> list[dict]:
            from azure.search.documents.knowledgebases.models import (
                KnowledgeBaseRetrievalRequest,
                KnowledgeRetrievalSemanticIntent,
                SearchIndexKnowledgeSourceParams,
            )

            client = get_knowledge_base_client(KNOWLEDGE_BASE_NAMES[knowledge_base])
            request = KnowledgeBaseRetrievalRequest(
                intents=[KnowledgeRetrievalSemanticIntent(search=query)],
                knowledge_source_params=[
                    SearchIndexKnowledgeSourceParams(
                        knowledge_source_name=knowledge_source_name(knowledge_base),
                        include_references=True,
                        include_reference_source_data=True,
                    )
                ],
            )
            response = client.retrieve(request)
            return [
                {
                    **(ref.source_data or {}),
                    "id": (ref.source_data or {}).get("id") or ref.doc_key,
                    "@search.reranker_score": ref.reranker_score,
                }
                for ref in response.references or []
                if ref.type == "searchIndex"
            ]

        rows = await _call(f"Foundry IQ {knowledge_base}", run)
        passages = sorted((_passage(row) for row in rows), key=lambda p: p.score, reverse=True)
        return passages[:top]


def _passage(row: dict[str, Any]) -> Passage:
    reranker = row.get("@search.reranker_score")
    score = reranker / _RERANKER_MAX if reranker is not None else 0.0
    try:
        metadata = json.loads(row.get("metadata_json") or "{}")
    except json.JSONDecodeError:
        metadata = {}
    return Passage(
        id=str(row.get("id", "")),
        title=row.get("title") or "",
        content=row.get("content") or "",
        source_doc=row.get("source_doc") or "",
        score=round(min(max(float(score), 0.0), 1.0), 3),
        metadata=metadata,
    )


def _query(container: str, sql: str, **params: str | int) -> Callable[[], list[dict]]:
    def run() -> list[dict]:
        client = get_cosmos_database().get_container_client(container)
        parameters = [{"name": f"@{k}", "value": v} for k, v in params.items()]
        return list(
            client.query_items(query=sql, parameters=parameters, enable_cross_partition_query=True)
        )

    return run


class CosmosEntityStore:
    """Queries the containers that `infra/create_cosmos_db.py` creates."""

    async def find_entity(self, name: str, entity_type: str | None = None) -> dict | None:
        sql = "SELECT * FROM c WHERE LOWER(c.name) = LOWER(@name)"
        params = {"name": name}
        if entity_type:
            sql += " AND c.entity_type = @type"
            params["type"] = entity_type
        rows = await _call("Cosmos entities", _query("entities", sql, **params))
        return rows[0] if rows else None

    async def find_pep(self, name: str) -> dict | None:
        sql = "SELECT * FROM c WHERE LOWER(c.name) = LOWER(@name) AND c.is_pep = true"
        rows = await _call("Cosmos entities", _query("entities", sql, name=name))
        return rows[0] if rows else None

    async def ownership_children(self, parent_name: str) -> list[dict]:
        sql = "SELECT * FROM c WHERE LOWER(c.parent_entity) = LOWER(@name)"
        return await _call(
            "Cosmos corporate_graph", _query("corporate_graph", sql, name=parent_name)
        )

    async def transactions(self, entity_name: str, limit: int = 500) -> list[dict]:
        sql = (
            "SELECT * FROM c WHERE LOWER(c.entity_name) = LOWER(@name) "
            "ORDER BY c.date DESC OFFSET 0 LIMIT @limit"
        )
        query = _query("transactions", sql, name=entity_name, limit=int(limit))
        return await _call("Cosmos transactions", query)


class CosmosReportStore:
    """One document per report in `kyc_reports`, partitioned by report ID."""

    async def _read(self, report_id: str) -> dict | None:
        sql = "SELECT * FROM c WHERE c.report_id = @id"
        rows = await _call("Cosmos kyc_reports", _query(REPORTS_CONTAINER, sql, id=report_id))
        return rows[0] if rows else None

    async def _current(self, report_id: str) -> dict:
        return await self._read(report_id) or {"id": report_id, "report_id": report_id}

    async def _write(self, item: dict) -> None:
        def run() -> None:
            get_cosmos_database().get_container_client(REPORTS_CONTAINER).upsert_item(item)

        await _call("Cosmos kyc_reports", run)

    async def _upsert(self, report_id: str, **fields: Any) -> None:
        await self._write({**await self._current(report_id), **fields})

    async def save_status(self, report_id: str, status: str) -> None:
        await self._upsert(report_id, status=status)

    async def status(self, report_id: str) -> str | None:
        item = await self._read(report_id)
        return item.get("status") if item else None

    async def save_report(self, report_id: str, report: dict) -> None:
        await self._upsert(report_id, report=report)

    async def report(self, report_id: str) -> dict | None:
        item = await self._read(report_id)
        return item.get("report") if item else None

    async def append_event(self, report_id: str, event: dict) -> None:
        item = await self._current(report_id)
        await self._write({**item, "events": [*item.get("events", []), event]})

    async def events(self, report_id: str) -> list[dict]:
        item = await self._read(report_id)
        return list(item.get("events", [])) if item else []


# Document Intelligence's ID model names fields differently from ARGUS's validators.
_ID_FIELDS = {
    "DateOfBirth": "date_of_birth",
    "Nationality": "nationality",
    "DocumentNumber": "document_number",
    "DateOfExpiration": "expiry_date",
    "CountryRegion": "issuing_country",
    "Address": "address",
}


class DocumentIntelligenceOCR:
    async def extract(self, image: bytes, doc_type: str) -> dict[str, dict]:
        def run() -> dict[str, dict]:
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

            poller = get_document_intelligence_client().begin_analyze_document(
                "prebuilt-idDocument", AnalyzeDocumentRequest(bytes_source=image)
            )
            return _id_fields(poller.result())

        return await _call("Document Intelligence", run)


def _id_fields(result: Any) -> dict[str, dict]:
    fields: dict[str, dict] = {}
    for document in result.documents or []:
        found = document.fields or {}
        names = [found[k].content for k in ("FirstName", "LastName") if found.get(k)]
        if names:
            confidence = min(found[k].confidence for k in ("FirstName", "LastName") if found.get(k))
            fields["full_name"] = {"value": " ".join(names), "confidence": confidence}
        for source, target in _ID_FIELDS.items():
            if field := found.get(source):
                fields[target] = {"value": field.content, "confidence": field.confidence}
    return fields
