"""The data plane's selection, its local implementations and the shared corpus."""

from pathlib import Path

import pytest

import argus.data_plane as dp
from argus.data_plane import corpus
from argus.data_plane.local import (
    LocalEntityStore,
    LocalOCR,
    LocalRetriever,
    MemoryReportStore,
    local_retriever,
)

from .conftest import FIXTURE_DATA

# ── selection ─────────────────────────────────────────────────────────────────


def test_local_is_the_default_backend():
    plane = dp.get_data_plane()

    assert plane.backend == "local"
    assert dp.get_data_plane() is plane  # built once, then reused


def test_azure_backend_builds_the_azure_parts(monkeypatch):
    monkeypatch.setenv("ARGUS_DATA_BACKEND", " Azure ")

    plane = dp.build_data_plane()

    assert plane.backend == "azure"
    assert type(plane.retriever).__name__ == "AzureSearchRetriever"
    assert type(plane.reports).__name__ == "CosmosReportStore"


def test_unknown_backend_is_rejected(monkeypatch):
    monkeypatch.setenv("ARGUS_DATA_BACKEND", "floppy")

    with pytest.raises(ValueError, match="floppy"):
        dp.configured_backend()


def test_data_dir_defaults_to_the_repository_data_folder(monkeypatch):
    monkeypatch.delenv("ARGUS_DATA_DIR")

    assert dp.data_dir() == Path(__file__).resolve().parents[1] / "data"


# ── local retrieval ───────────────────────────────────────────────────────────


def _doc(id_: str, title: str, content: str = "") -> dict:
    return {"id": id_, "title": title, "content": content, "source_doc": "s", "metadata_json": ""}


async def test_rare_words_outweigh_common_ones():
    retriever = LocalRetriever(
        {
            "sanctions": [
                _doc("1", "Gamma Group"),
                _doc("2", "Delta Group"),
                _doc("3", "Epsilon Group"),
                _doc("4", "Zeta Holdings"),
            ]
        }
    )

    hits = await retriever.search("sanctions", "Gamma Group")

    assert [p.id for p in hits][:1] == ["1"]
    assert hits[0].score == 1.0
    assert all(p.score < 0.5 for p in hits[1:])


async def test_ties_are_ordered_by_id_and_capped_at_top():
    retriever = LocalRetriever({"regulations": [_doc("b", "same"), _doc("a", "same")]})

    hits = await retriever.search("regulations", "same", top=1)

    assert [p.id for p in hits] == ["a"]


async def test_nothing_to_search_returns_nothing():
    retriever = LocalRetriever({"regulations": [_doc("a", "text")]})

    assert await retriever.search("regulations", "") == []
    assert await retriever.search("sanctions", "text") == []
    assert await retriever.search("regulations", "unrelated") == []


async def test_local_retriever_reads_the_data_folder():
    retriever = local_retriever(FIXTURE_DATA)

    hits = await retriever.search("adverse_media", "Example Bank enforcement")

    assert hits[0].id == "PUB-T1"
    assert hits[0].metadata["source_kind"] == "public"


# ── local stores ──────────────────────────────────────────────────────────────


async def test_entity_store_matches_names_and_types_case_insensitively():
    store = LocalEntityStore(FIXTURE_DATA)

    assert (await store.find_entity("ada SYNTHETIC"))["entity_id"] == "IND-T0001"
    assert await store.find_entity("Ada Synthetic", "corporate") is None
    assert await store.find_pep("Ada Synthetic") is None
    assert (await store.find_pep("Pat Politico"))["role"] == "Deputy minister"
    assert await store.find_pep("Nobody") is None


async def test_transactions_are_newest_first_and_limited():
    store = LocalEntityStore(FIXTURE_DATA)

    latest = await store.transactions("Ada Synthetic", limit=2)

    assert [t["date"] for t in latest] == ["2026-03-15", "2026-03-14"]


async def test_missing_data_files_mean_empty_collections(tmp_path):
    store = LocalEntityStore(tmp_path)

    assert await store.find_entity("Ada Synthetic") is None
    assert await store.ownership_children("Anything") == []
    assert await store.transactions("Anything") == []


async def test_memory_report_store_round_trip():
    store = MemoryReportStore()

    assert await store.status("r1") is None and await store.report("r1") is None
    await store.save_status("r1", "processing")
    await store.save_report("r1", {"ok": True})

    assert await store.status("r1") == "processing"
    assert await store.report("r1") == {"ok": True}


async def test_local_ocr_reports_it_cannot_read():
    with pytest.raises(dp.DataPlaneUnavailable):
        await LocalOCR().extract(b"image", "passport")


# ── corpus ────────────────────────────────────────────────────────────────────


def test_regulation_documents_carry_the_index_fields():
    docs = corpus.regulation_documents()

    assert {d["id"] for d in docs} >= {"fatf-rec-10", "fatf-rec-12", "fatf-rec-20"}
    assert all(d["entity_name"] == "" and d["metadata_json"] == "{}" for d in docs)


def test_sanctions_documents_index_every_name():
    [doc] = corpus.sanctions_documents(
        [{"sanctions_id": "S1", "name": "Viktor", "aliases": ["V."], "nationality": "RU"}]
    )

    assert doc["entity_name"] == "Viktor | V."
    assert doc["title"] == "Viktor — SANCTIONS"
    assert "Nationality/Country: RU." in doc["content"]


def test_adverse_media_documents_keep_negative_coverage_only():
    docs = corpus.adverse_media_documents(
        [
            {"id": "a", "sentiment": "negative", "headline": "H"},
            {"id": "b", "sentiment": "positive"},
        ],
        [{"document_id": "p", "body": "B"}],
    )

    assert [d["id"] for d in docs] == ["a", "p"]
    assert docs[0]["content"] == "H"  # no body: the headline is the content
    assert '"source_kind": "public"' in docs[1]["metadata_json"]


def test_load_jsonl_skips_blank_lines(tmp_path):
    path = tmp_path / "x.jsonl"
    path.write_text('{"a": 1}\n\n{"a": 2}\n', encoding="utf-8")

    assert corpus.load_jsonl(path) == [{"a": 1}, {"a": 2}]
    assert corpus.load_jsonl(tmp_path / "missing.jsonl") == []
