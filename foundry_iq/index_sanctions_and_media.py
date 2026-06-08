"""
index_sanctions.py + index_adverse_media.py
Index synthetic and public-source datasets into Foundry IQ knowledge bases.
"""
import os, json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.env_loader import load_repo_env

load_repo_env(__file__)

# ── Sanctions ─────────────────────────────────────────────────────────────────

SANCTIONS_FILE = Path(__file__).parent.parent / "data" / "synthetic" / "sanctions.jsonl"
SANCTIONS_KB   = os.getenv("FOUNDRY_IQ_KB_SANCTIONS", "argus-kb-sanctions")

def index_sanctions():
    print(f"Indexing synthetic sanctions into {SANCTIONS_KB}...")
    if not SANCTIONS_FILE.exists():
        print("  sanctions.jsonl not found. Run: python data/synthetic/generate_sanctions.py")
        return

    records = [json.loads(line) for line in SANCTIONS_FILE.read_text().splitlines() if line.strip()]
    print(f"  Loaded {len(records)} synthetic sanctions entries")

    docs = []
    for r in records:
        aliases   = r.get("aliases", [])
        name      = r.get("name", "")
        all_names = " | ".join([name] + aliases)
        content   = (
            f"{name}. Aliases: {', '.join(aliases)}. "
            f"List: {r.get('list_type', '')}. Program: {r.get('program', '')}. "
            f"Reason: {r.get('reason', '')}. "
            f"Nationality/Country: {r.get('nationality') or r.get('country', '')}."
        )
        docs.append({
            "id":            r["sanctions_id"],
            "title":         f"{name} — {r.get('list_type', 'SANCTIONS')}",
            "content":       content,
            "entity_name":   all_names,
            "source_doc":    r.get("list_type", "SYNTHETIC_SANCTIONS"),
            "category":      "sanctions",
            "metadata_json": json.dumps({
                "program":    r.get("program"),
                "is_active":  r.get("is_active"),
                "entity_type": r.get("entity_type"),
            }),
        })

    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key      = os.environ["AZURE_SEARCH_API_KEY"]
        client   = SearchClient(endpoint, SANCTIONS_KB, AzureKeyCredential(key))

        # Upload in batches of 100 (AI Search limit per call)
        batch_size = 100
        total_ok   = 0
        for i in range(0, len(docs), batch_size):
            batch  = docs[i:i + batch_size]
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

MEDIA_FILE = Path(__file__).parent.parent / "data" / "synthetic" / "adverse_media.jsonl"
PUBLIC_MEDIA_FILE = Path(__file__).parent.parent / "data" / "public" / "adverse_media_public.jsonl"
MEDIA_KB   = os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA", "argus-kb-adversemedia")
ADVERSE_MEDIA_EXPORT = Path(__file__).parent.parent / "data" / "public" / "adverse_media_index_payload.jsonl"


def _load_jsonl_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _build_adverse_media_documents() -> list[dict]:
    synthetic_records = _load_jsonl_records(MEDIA_FILE)
    public_records = _load_jsonl_records(PUBLIC_MEDIA_FILE)

    if not synthetic_records and not public_records:
        return []

    negative_only = [r for r in synthetic_records if r.get("sentiment") == "negative"]
    public_negative = [r for r in public_records if r.get("sentiment", "negative") == "negative"]

    docs = []
    for r in [*negative_only, *public_negative]:
        docs.append({
            "id":            r.get("article_id") or r.get("document_id") or r.get("id"),
            "title":         r.get("headline", "")[:200],
            "content":       r.get("body", r.get("headline", ""))[:2000],
            "entity_name":   "",           # entity extracted at query time
            "source_doc":    r.get("source", "SYNTHETIC_NEWS"),
            "category":      "adverse_media",
            "metadata_json": json.dumps({
                "source_kind":  r.get("source_kind", "synthetic" if r in negative_only else "public"),
                "published_at": r.get("published_at"),
                "sentiment":    r.get("sentiment"),
                "tags":         r.get("tags", []),
                "source_reference": r.get("source_reference"),
            }),
        })

    return docs


def _export_adverse_media_documents(docs: list[dict]) -> None:
    ADVERSE_MEDIA_EXPORT.parent.mkdir(parents=True, exist_ok=True)
    with ADVERSE_MEDIA_EXPORT.open("w", encoding="utf-8") as handle:
        for doc in docs:
            handle.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(f"  ℹ️  Azure SDK unavailable. Exported {len(docs)} index payload docs -> {ADVERSE_MEDIA_EXPORT}")


def _upload_documents_via_rest(index_name: str, docs: list[dict]) -> int:
    import urllib.request

    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/")
    key = os.environ["AZURE_SEARCH_API_KEY"]
    uploaded = 0
    batch_size = 100

    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        payload = {
            "value": [{"@search.action": "mergeOrUpload", **doc} for doc in batch]
        }
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
        print("  adverse_media.jsonl not found. Run: python data/synthetic/generate_adverse_media.py")
        return

    synthetic_records = _load_jsonl_records(MEDIA_FILE)
    public_records = _load_jsonl_records(PUBLIC_MEDIA_FILE)
    negative_only = [r for r in synthetic_records if r.get("sentiment") == "negative"]
    public_negative = [r for r in public_records if r.get("sentiment", "negative") == "negative"]
    print(f"  Loaded {len(negative_only)} synthetic negative articles (from {len(synthetic_records)} total)")
    if public_records:
        print(f"  Loaded {len(public_negative)} public adverse-media records (from {len(public_records)} total)")

    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key      = os.environ["AZURE_SEARCH_API_KEY"]
        client   = SearchClient(endpoint, MEDIA_KB, AzureKeyCredential(key))

        batch_size = 100
        total_ok   = 0
        for i in range(0, len(docs), batch_size):
            batch  = docs[i:i + batch_size]
            result = client.upload_documents(batch)
            total_ok += sum(1 for r in result if r.succeeded)

        print(f"  ✅ {total_ok}/{len(docs)} adverse media articles indexed into {MEDIA_KB}")
    except ImportError:
        uploaded = _upload_documents_via_rest(MEDIA_KB, docs)
        print(f"  ✅ {uploaded}/{len(docs)} adverse media articles indexed into {MEDIA_KB} via REST")
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
