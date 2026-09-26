"""Local data plane: synthetic data from `data/`, searched and stored in memory.

Needs no network and no credentials. Missing data files mean empty collections, not errors: a
fresh clone without generated data still runs, and simply finds nothing.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import cached_property
from pathlib import Path

from argus.data_plane.base import DataPlaneUnavailable, KnowledgeBase, Passage
from argus.data_plane.corpus import (
    adverse_media_documents,
    load_jsonl,
    regulation_documents,
    sanctions_documents,
)

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if len(t) > 1}


class LocalRetriever:
    """Keyword retrieval weighted by rarity.

    A passage's score is the share of the query's weight it contains, where rare words weigh
    more (inverse document frequency). So a passage matching a distinctive name scores high, and
    one matching only common words ("group", "ltd") scores low.
    """

    def __init__(self, corpora: dict[KnowledgeBase, list[dict]]):
        self._docs = {
            kb: [(doc, _tokens(_searchable(doc))) for doc in docs] for kb, docs in corpora.items()
        }
        self._idf = {kb: _idf([tokens for _, tokens in docs]) for kb, docs in self._docs.items()}

    async def search(
        self, knowledge_base: KnowledgeBase, query: str, top: int = 5
    ) -> list[Passage]:
        docs = self._docs.get(knowledge_base, [])
        idf = self._idf.get(knowledge_base, {})
        query_tokens = _tokens(query)
        unseen = math.log(len(docs) + 1) + 1  # a word no document has weighs the most
        total = sum(idf.get(t, unseen) for t in query_tokens)
        if not docs or not total:
            return []
        scored = []
        for doc, tokens in docs:
            matched = sum(idf[t] for t in query_tokens & tokens)
            if matched:
                scored.append((round(matched / total, 3), doc))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
        return [_passage(doc, score) for score, doc in scored[:top]]


def _searchable(doc: dict) -> str:
    return " ".join(str(doc.get(key, "")) for key in ("title", "content", "entity_name"))


def _idf(documents: list[set[str]]) -> dict[str, float]:
    counts: Counter[str] = Counter()
    for tokens in documents:
        counts.update(tokens)
    n = len(documents)
    return {token: math.log((n + 1) / (count + 0.5)) + 1 for token, count in counts.items()}


def _passage(doc: dict, score: float) -> Passage:
    return Passage(
        id=str(doc["id"]),
        title=doc.get("title", ""),
        content=doc.get("content", ""),
        source_doc=doc.get("source_doc", ""),
        score=score,
        metadata=json.loads(doc.get("metadata_json") or "{}"),
    )


class LocalEntityStore:
    """Synthetic entities, ownership graph and transactions from `data/synthetic/*.jsonl`."""

    def __init__(self, data_dir: Path):
        self._dir = data_dir / "synthetic"

    @cached_property
    def _entities(self) -> list[dict]:
        return load_jsonl(self._dir / "entities.jsonl")

    @cached_property
    def _graph(self) -> list[dict]:
        return load_jsonl(self._dir / "corporate_graph.jsonl")

    @cached_property
    def _transactions(self) -> list[dict]:
        return load_jsonl(self._dir / "transactions.jsonl")

    async def find_entity(self, name: str, entity_type: str | None = None) -> dict | None:
        wanted = name.strip().lower()
        for record in self._entities:
            if record.get("name", "").lower() == wanted and entity_type in (
                None,
                record.get("entity_type"),
            ):
                return record
        return None

    async def find_pep(self, name: str) -> dict | None:
        record = await self.find_entity(name)
        return record if record and record.get("is_pep") else None

    async def ownership_children(self, parent_name: str) -> list[dict]:
        wanted = parent_name.strip().lower()
        return [n for n in self._graph if n.get("parent_entity", "").lower() == wanted]

    async def transactions(self, entity_name: str, limit: int = 500) -> list[dict]:
        wanted = entity_name.strip().lower()
        matches = [t for t in self._transactions if t.get("entity_name", "").lower() == wanted]
        return sorted(matches, key=lambda t: t.get("date", ""), reverse=True)[:limit]


class MemoryReportStore:
    """Reports kept for the life of the process. Lost on restart, so local use only."""

    def __init__(self) -> None:
        self._status: dict[str, str] = {}
        self._reports: dict[str, dict] = {}

    async def save_status(self, report_id: str, status: str) -> None:
        self._status[report_id] = status

    async def status(self, report_id: str) -> str | None:
        return self._status.get(report_id)

    async def save_report(self, report_id: str, report: dict) -> None:
        self._reports[report_id] = report

    async def report(self, report_id: str) -> dict | None:
        return self._reports.get(report_id)


class LocalOCR:
    """No local OCR engine yet, so every document reports as unreadable."""

    async def extract(self, image: bytes, doc_type: str) -> dict[str, dict]:
        raise DataPlaneUnavailable("No local OCR engine is installed")


def local_retriever(data_dir: Path) -> LocalRetriever:
    synthetic = data_dir / "synthetic"
    return LocalRetriever(
        {
            "regulations": regulation_documents(),
            "sanctions": sanctions_documents(load_jsonl(synthetic / "sanctions.jsonl")),
            "adverse_media": adverse_media_documents(
                load_jsonl(synthetic / "adverse_media.jsonl"),
                load_jsonl(data_dir / "public" / "adverse_media_public.jsonl"),
            ),
        }
    )
