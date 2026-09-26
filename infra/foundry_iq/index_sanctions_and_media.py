"""
index_sanctions.py + index_adverse_media.py
Index synthetic and public-source datasets into Foundry IQ knowledge bases.
"""

import json
import os
import sys
from pathlib import Path

from argus.data_plane.corpus import adverse_media_documents, sanctions_documents
from argus.utils.env_loader import load_repo_env

ROOT = Path(__file__).resolve().parents[2]

load_repo_env(__file__)

# ── Sanctions ─────────────────────────────────────────────────────────────────

SANCTIONS_FILE = ROOT / "data" / "synthetic" / "sanctions.jsonl"
SANCTIONS_KB = os.getenv("FOUNDRY_IQ_KB_SANCTIONS", "argus-kb-sanctions")


def index_sanctions():
    print(f"Indexing synthetic sanctions into {SANCTIONS_KB}...")
    if not SANCTIONS_FILE.exists():
        print("  sanctions.jsonl not found. Run: python data/synthetic/generate_sanctions.py")
        return

    records = [json.loads(line) for line in SANCTIONS_FILE.read_text().splitlines() if line.strip()]
    print(f"  Loaded {len(records)} synthetic sanctions entries")

    docs = sanctions_documents(records)

    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key = os.environ["AZURE_SEARCH_API_KEY"]
        client = SearchClient(endpoint, SANCTIONS_KB, AzureKeyCredential(key))

        # Upload in batches of 100 (AI Search limit per call)
        batch_size = 100
        total_ok = 0
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            result = client.upload_documents(batch)
            total_ok += sum(1 for r in result if r.succeeded)

        print(f"  ✅ {total_ok}/{len(docs)} sanctions entries indexed into {SANCTIONS_KB}")
    except ImportError:
        uploaded = _upload_documents_via_rest(SANCTIONS_KB, docs)
        print(f"  ✅ {uploaded}/{len(docs)} sanctions entries indexed into {SANCTIONS_KB} via REST")
    except Exception as e:
        print(f"  ❌ Error indexing sanctions: {e}")
        raise


# ── Adverse Media ─────────────────────────────────────────────────────────────

MEDIA_FILE = ROOT / "data" / "synthetic" / "adverse_media.jsonl"
PUBLIC_MEDIA_FILE = ROOT / "data" / "public" / "adverse_media_public.jsonl"
MEDIA_KB = os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA", "argus-kb-adversemedia")
ADVERSE_MEDIA_EXPORT = ROOT / "data" / "public" / "adverse_media_index_payload.jsonl"


def _load_jsonl_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _build_adverse_media_documents() -> list[dict]:
    return adverse_media_documents(
        _load_jsonl_records(MEDIA_FILE), _load_jsonl_records(PUBLIC_MEDIA_FILE)
    )


def _export_adverse_media_documents(docs: list[dict]) -> None:
    ADVERSE_MEDIA_EXPORT.parent.mkdir(parents=True, exist_ok=True)
    with ADVERSE_MEDIA_EXPORT.open("w", encoding="utf-8") as handle:
        for doc in docs:
            handle.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(
        f"  ℹ️  Azure SDK unavailable. Exported {len(docs)} index payload docs -> {ADVERSE_MEDIA_EXPORT}"
    )


def _upload_documents_via_rest(index_name: str, docs: list[dict]) -> int:
    import urllib.request

    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/")
    key = os.environ["AZURE_SEARCH_API_KEY"]
    uploaded = 0
    batch_size = 100

    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        payload = {"value": [{"@search.action": "mergeOrUpload", **doc} for doc in batch]}
        request = urllib.request.Request(
            f"{endpoint}/indexes/{index_name}/docs/index?api-version=2023-11-01",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "api-key": key,
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            response.read()
        uploaded += len(batch)

    return uploaded


def index_adverse_media():
    print(f"Indexing synthetic adverse media into {MEDIA_KB}...")

    docs = _build_adverse_media_documents()

    if not docs:
        print(
            "  adverse_media.jsonl not found. Run: python data/synthetic/generate_adverse_media.py"
        )
        return

    synthetic_records = _load_jsonl_records(MEDIA_FILE)
    public_records = _load_jsonl_records(PUBLIC_MEDIA_FILE)
    negative_only = [r for r in synthetic_records if r.get("sentiment") == "negative"]
    public_negative = [r for r in public_records if r.get("sentiment", "negative") == "negative"]
    print(
        f"  Loaded {len(negative_only)} synthetic negative articles (from {len(synthetic_records)} total)"
    )
    if public_records:
        print(
            f"  Loaded {len(public_negative)} public adverse-media records (from {len(public_records)} total)"
        )

    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key = os.environ["AZURE_SEARCH_API_KEY"]
        client = SearchClient(endpoint, MEDIA_KB, AzureKeyCredential(key))

        batch_size = 100
        total_ok = 0
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            result = client.upload_documents(batch)
            total_ok += sum(1 for r in result if r.succeeded)

        print(f"  ✅ {total_ok}/{len(docs)} adverse media articles indexed into {MEDIA_KB}")
    except ImportError:
        uploaded = _upload_documents_via_rest(MEDIA_KB, docs)
        print(
            f"  ✅ {uploaded}/{len(docs)} adverse media articles indexed into {MEDIA_KB} via REST"
        )
    except Exception as e:
        print(f"  ❌ Error indexing adverse media: {e}")
        raise


if __name__ == "__main__":
    import sys

    if "sanctions" in sys.argv[0]:
        index_sanctions()
    elif "adverse" in sys.argv[0]:
        index_adverse_media()
    else:
        index_sanctions()
        index_adverse_media()
