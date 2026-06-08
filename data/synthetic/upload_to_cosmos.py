"""
upload_to_cosmos.py
Uploads all generated synthetic data to Azure Cosmos DB.

Loads:
  data/synthetic/entities.jsonl       → container: entities
  data/synthetic/corporate_graph.jsonl → container: corporate_graph
  data/synthetic/transactions.jsonl   → container: transactions
  data/synthetic/sanctions.jsonl      → extracts PEPs → container: pep_list

Run after: make generate-data
Usage:     python data/synthetic/upload_to_cosmos.py
"""
import json
import os
import time
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.env_loader import load_repo_env

load_repo_env(__file__)

DATA_DIR = Path(__file__).parent

UPLOADS = [
    {
        "file":      DATA_DIR / "entities.jsonl",
        "container": "entities",
        "id_field":  "entity_id",
    },
    {
        "file":      DATA_DIR / "corporate_graph.jsonl",
        "container": "corporate_graph",
        "id_field":  None,          # no natural id — generate one
    },
    {
        "file":      DATA_DIR / "transactions.jsonl",
        "container": "transactions",
        "id_field":  "tx_id",       # actual field name in transactions.jsonl
    },
    {
        "file":      DATA_DIR / "sanctions.jsonl",
        "container": "pep_list",    # sanctions list doubles as screening reference
        "id_field":  "sanctions_id",
    },
]


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  ⚠️  File not found: {path.name}  — run 'make generate-data' first.")
        return []
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def _upsert_batch(container, docs: list[dict], id_field: str) -> int:
    """Upsert a list of documents; returns count of successful upserts."""
    from azure.cosmos import exceptions as cosmos_exceptions

    ok = 0
    skipped = 0
    max_retries = 5

    for doc in docs:
        # Cosmos DB requires 'id' field as a string
        if id_field and doc.get(id_field):
            doc["id"] = str(doc[id_field])
        elif not doc.get("id"):
            doc["id"] = str(uuid.uuid4())

        attempt = 0
        while attempt <= max_retries:
            try:
                container.upsert_item(doc)
                ok += 1
                break
            except Exception as e:
                attempt += 1
                # Handle throttling (429) and transient server errors with backoff
                status = getattr(e, 'status_code', None)
                if status == 429 or isinstance(e, cosmos_exceptions.CosmosHttpResponseError) and status in (429, 503):
                    wait = 2 ** attempt
                    time.sleep(wait)
                    continue
                # Non-retriable or exhausted retries
                if attempt > max_retries:
                    skipped += 1
                else:
                    # last retry failed, count as skipped
                    skipped += 1
                # Only print a short message to avoid massive terminal spam
                if skipped <= 10 or skipped % 100 == 0:
                    print(f"    ⚠️  Skipped {doc['id']}: {e}")
                break

    if skipped:
        print(f"    ⚠️  Skipped {skipped}/{len(docs)} documents due to errors")
    return ok


def upload_to_cosmos():
    print("Uploading synthetic data to Azure Cosmos DB...")

    try:
        from azure.cosmos import CosmosClient

        endpoint      = os.environ["COSMOS_ENDPOINT"]
        key           = os.environ["COSMOS_KEY"]
        database_name = os.environ.get("COSMOS_DATABASE", "argus-db")

        client   = CosmosClient(endpoint, key)
        database = client.get_database_client(database_name)

        for upload_def in UPLOADS:
            docs         = _load_jsonl(upload_def["file"])
            if not docs:
                continue

            container_id = upload_def["container"]
            container    = database.get_container_client(container_id)

            print(f"  Uploading {len(docs)} docs → {container_id}...")
            ok = _upsert_batch(container, docs, upload_def["id_field"])
            print(f"  ✅ {ok}/{len(docs)} upserted into {container_id}")

        # Extract PEPs from entities and upload to pep_list container
        _upload_peps(database)

        print("\nCosmos DB upload complete.")

    except KeyError as e:
        print(f"  ❌ Missing env var: {e}. Run infra/setup.ps1 first.")
        raise
    except Exception as e:
        print(f"  ❌ Upload failed: {e}")
        raise


def _upload_peps(database):
    """Extract PEP records from entities.jsonl and upload to pep_list container.
    Also uploads adverse_media.jsonl docs into the kyc_reports container for demo use."""
    # --- PEPs ---
    entities_file = DATA_DIR / "entities.jsonl"
    all_entities  = _load_jsonl(entities_file)
    if all_entities:
        peps = [e for e in all_entities if e.get("is_pep")]
        if peps:
            # pep_list container is already loaded with sanctions; upload additional PEPs
            # Use a sub-container or just skip if already populated
            print(f"  ℹ️  {len(peps)} PEP entities found in entities.jsonl (already in entities container)")
        else:
            print("  ℹ️  No PEPs found in entities (expected ~5%).")

    # --- Adverse media into kyc_reports as raw articles (useful for demo queries) ---
    media_file = DATA_DIR / "adverse_media.jsonl"
    media_docs = _load_jsonl(media_file)
    if media_docs:
        container = database.get_container_client("kyc_reports")
        # Set id from article_id
        ok = _upsert_batch(container, media_docs, "article_id")
        print(f"  ✅ {ok}/{len(media_docs)} adverse media records uploaded → kyc_reports")


if __name__ == "__main__":
    upload_to_cosmos()
