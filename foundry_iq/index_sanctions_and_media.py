"""
index_sanctions.py + index_adverse_media.py
Index synthetic datasets into Foundry IQ knowledge bases.
"""
import os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

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

    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential
        import json as _json

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key      = os.environ["AZURE_SEARCH_API_KEY"]
        client   = SearchClient(endpoint, SANCTIONS_KB, AzureKeyCredential(key))

        # Transform JSONL records into search documents
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
                "metadata_json": _json.dumps({
                    "program":    r.get("program"),
                    "is_active":  r.get("is_active"),
                    "entity_type": r.get("entity_type"),
                }),
            })

        # Upload in batches of 100 (AI Search limit per call)
        batch_size = 100
        total_ok   = 0
        for i in range(0, len(docs), batch_size):
            batch  = docs[i:i + batch_size]
            result = client.upload_documents(batch)
            total_ok += sum(1 for r in result if r.succeeded)

        print(f"  ✅ {total_ok}/{len(docs)} sanctions entries indexed into {SANCTIONS_KB}")
    except Exception as e:
        print(f"  ❌ Error indexing sanctions: {e}")
        raise


# ── Adverse Media ─────────────────────────────────────────────────────────────

MEDIA_FILE = Path(__file__).parent.parent / "data" / "synthetic" / "adverse_media.jsonl"
MEDIA_KB   = os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA", "argus-kb-adversemedia")

def index_adverse_media():
    print(f"Indexing synthetic adverse media into {MEDIA_KB}...")
    if not MEDIA_FILE.exists():
        print("  adverse_media.jsonl not found. Run: python data/synthetic/generate_adverse_media.py")
        return

    records = [json.loads(line) for line in MEDIA_FILE.read_text().splitlines() if line.strip()]
    negative_only = [r for r in records if r.get("sentiment") == "negative"]
    print(f"  Loaded {len(negative_only)} negative articles (from {len(records)} total)")

    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential
        import json as _json

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key      = os.environ["AZURE_SEARCH_API_KEY"]
        client   = SearchClient(endpoint, MEDIA_KB, AzureKeyCredential(key))

        docs = []
        for r in negative_only:
            docs.append({
                "id":            r["article_id"],
                "title":         r.get("headline", "")[:200],
                "content":       r.get("body", r.get("headline", ""))[:2000],
                "entity_name":   "",           # entity extracted at query time
                "source_doc":    r.get("source", "SYNTHETIC_NEWS"),
                "category":      "adverse_media",
                "metadata_json": _json.dumps({
                    "published_at": r.get("published_at"),
                    "sentiment":    r.get("sentiment"),
                    "tags":         r.get("tags", []),
                }),
            })

        batch_size = 100
        total_ok   = 0
        for i in range(0, len(docs), batch_size):
            batch  = docs[i:i + batch_size]
            result = client.upload_documents(batch)
            total_ok += sum(1 for r in result if r.succeeded)

        print(f"  ✅ {total_ok}/{len(docs)} adverse media articles indexed into {MEDIA_KB}")
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
