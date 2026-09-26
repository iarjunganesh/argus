"""The data plane: where ARGUS reads entities and documents, and keeps reports.

`ARGUS_DATA_BACKEND` chooses the implementation set:

- `local` (default): synthetic data from `ARGUS_DATA_DIR` (default: the repository's `data/`),
  searched and stored in memory. No network, no cost.
- `azure`: Azure AI Search, Cosmos DB and Document Intelligence, configured by the settings in
  `.env.example`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from argus.data_plane.base import (
    OCR,
    DataPlaneUnavailable,
    EntityStore,
    KnowledgeBase,
    Passage,
    ReportStore,
    Retriever,
)

Backend = Literal["local", "azure"]
BACKENDS: tuple[Backend, ...] = ("local", "azure")

__all__ = [
    "OCR",
    "DataPlane",
    "DataPlaneUnavailable",
    "EntityStore",
    "KnowledgeBase",
    "Passage",
    "ReportStore",
    "Retriever",
    "get_data_plane",
    "set_data_plane",
]


@dataclass(frozen=True)
class DataPlane:
    backend: Backend
    retriever: Retriever
    entities: EntityStore
    reports: ReportStore
    ocr: OCR


def configured_backend() -> Backend:
    value = os.getenv("ARGUS_DATA_BACKEND", "local").strip().lower()
    if value not in BACKENDS:
        raise ValueError(f"ARGUS_DATA_BACKEND must be one of {', '.join(BACKENDS)}, not {value!r}")
    return cast(Backend, value)


def data_dir() -> Path:
    # src/argus/data_plane/__init__.py -> the repository root is three levels up.
    default = Path(__file__).resolve().parents[3] / "data"
    return Path(os.getenv("ARGUS_DATA_DIR") or default)


_active: DataPlane | None = None


def get_data_plane() -> DataPlane:
    """The data plane in use, built from the settings on first use."""
    global _active
    if _active is None:
        _active = build_data_plane()
    return _active


def set_data_plane(plane: DataPlane | None) -> None:
    """Install a data plane (tests use this); `None` rebuilds from the settings on next use."""
    global _active
    _active = plane


def build_data_plane() -> DataPlane:
    if configured_backend() == "azure":
        from argus.data_plane import azure

        return DataPlane(
            backend="azure",
            retriever=azure.AzureSearchRetriever(),
            entities=azure.CosmosEntityStore(),
            reports=azure.CosmosReportStore(),
            ocr=azure.DocumentIntelligenceOCR(),
        )

    from argus.data_plane import local

    directory = data_dir()
    return DataPlane(
        backend="local",
        retriever=local.local_retriever(directory),
        entities=local.LocalEntityStore(directory),
        reports=local.MemoryReportStore(),
        ocr=local.LocalOCR(),
    )
