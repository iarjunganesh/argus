"""
index_sanctions_and_media.py
Index the synthetic sanctions list and the adverse media articles into their Foundry IQ knowledge
bases. Each index ends up holding exactly the documents built here (replace_documents.py).
"""

import json
import os
from pathlib import Path

from replace_documents import replace_documents

from argus.data_plane.corpus import adverse_media_documents, sanctions_documents
from argus.utils.env_loader import load_repo_env

ROOT = Path(__file__).resolve().parents[2]

load_repo_env(__file__)


def _client(index_name: str):
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key = os.environ["AZURE_SEARCH_API_KEY"]
    return SearchClient(endpoint, index_name, AzureKeyCredential(key))


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

    stale = replace_documents(_client(SANCTIONS_KB), docs)
    print(f"  ✅ {len(docs)} sanctions entries indexed into {SANCTIONS_KB}; {stale} stale removed")


# ── Adverse Media ─────────────────────────────────────────────────────────────

MEDIA_FILE = ROOT / "data" / "synthetic" / "adverse_media.jsonl"
PUBLIC_MEDIA_FILE = ROOT / "data" / "public" / "adverse_media_public.jsonl"
MEDIA_KB = os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA", "argus-kb-adversemedia")


def _load_jsonl_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _build_adverse_media_documents() -> list[dict]:
    return adverse_media_documents(
        _load_jsonl_records(MEDIA_FILE), _load_jsonl_records(PUBLIC_MEDIA_FILE)
    )


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

    stale = replace_documents(_client(MEDIA_KB), docs)
    print(f"  ✅ {len(docs)} adverse media articles indexed into {MEDIA_KB}; {stale} stale removed")


if __name__ == "__main__":
    index_sanctions()
    index_adverse_media()
