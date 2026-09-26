"""The four data-plane interfaces (decision D6) and the values they exchange.

Every agent tool reaches data through one of these interfaces. Each has exactly two
implementations: Azure (`argus.data_plane.azure`) and local (`argus.data_plane.local`), chosen
by `ARGUS_DATA_BACKEND`. The local set needs no network, so CI and the zero-cost baseline run on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

KnowledgeBase = Literal["regulations", "sanctions", "adverse_media"]
KNOWLEDGE_BASES: tuple[KnowledgeBase, ...] = ("regulations", "sanctions", "adverse_media")


class DataPlaneUnavailable(RuntimeError):
    """A data service could not answer.

    Tools catch this, fall back to a result that asserts nothing, and label it `fallback`, so a
    report never presents a substitute as if it came from data.
    """


@dataclass(frozen=True)
class Passage:
    """One retrieved document, with the fields a citation needs."""

    id: str
    title: str
    content: str
    source_doc: str
    score: float  # 0 to 1, higher is more relevant
    metadata: dict[str, Any] = field(default_factory=dict)


class Retriever(Protocol):
    async def search(
        self, knowledge_base: KnowledgeBase, query: str, top: int = 5
    ) -> list[Passage]: ...


class EntityStore(Protocol):
    async def find_entity(self, name: str, entity_type: str | None = None) -> dict | None: ...

    async def find_pep(self, name: str) -> dict | None: ...

    async def ownership_children(self, parent_name: str) -> list[dict]: ...

    async def transactions(self, entity_name: str, limit: int = 500) -> list[dict]: ...


class ReportStore(Protocol):
    """The only code that writes assessment reports and their status."""

    async def save_status(self, report_id: str, status: str) -> None: ...

    async def status(self, report_id: str) -> str | None: ...

    async def save_report(self, report_id: str, report: dict) -> None: ...

    async def report(self, report_id: str) -> dict | None: ...


class OCR(Protocol):
    async def extract(self, image: bytes, doc_type: str) -> dict[str, dict]:
        """Return `{field_name: {"value": str, "confidence": float}}` for the document."""
        ...
