"""
upload_to_cosmos.py
Makes the Cosmos DB containers hold exactly the generated synthetic data.

Loads:
  data/synthetic/entities.jsonl        → container: entities
  data/synthetic/corporate_graph.jsonl → container: corporate_graph
  data/synthetic/transactions.jsonl    → container: transactions

Each record is upserted, then every item the data no longer contains is deleted, so a rerun after
the data is regenerated leaves nothing stale. A record the service rejects stops the run with an
error instead of being counted as uploaded. Sanctions and adverse media are not in Cosmos: they
are search indexes (infra/foundry_iq/). Reports live in `kyc_reports`, which this never touches.

Run after the generate_*.py scripts in this folder and a deployment (docs/DEPLOYMENT.md).
Usage:     uv run python data/synthetic/upload_to_cosmos.py
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

from argus.utils.env_loader import load_repo_env

load_repo_env(__file__)

DATA_DIR = Path(__file__).parent

# Each partition key matches infra/main.bicep (tests/test_data_plane_azure.py checks both).
UPLOADS = [
    {
        "file": "entities.jsonl",
        "container": "entities",
        "id_field": "entity_id",
        "partition_key": "entity_type",
    },
    {
        "file": "corporate_graph.jsonl",
        "container": "corporate_graph",
        "id_field": None,
        "partition_key": "parent_entity",
    },
    {
        "file": "transactions.jsonl",
        "container": "transactions",
        "id_field": "tx_id",
        "partition_key": "entity_name",
    },
]


class UploadFailed(RuntimeError):
    """Cosmos DB rejected records; the message names a few of them."""


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def with_ids(docs: list[dict], id_field: str | None) -> list[dict]:
    """Each record with the string `id` Cosmos needs: its own ID field, or one derived from its
    content, so the same record keeps the same ID from run to run."""
    out = []
    for doc in docs:
        if id_field:
            item_id = str(doc[id_field])
        else:
            item_id = str(uuid.uuid5(uuid.NAMESPACE_URL, json.dumps(doc, sort_keys=True)))
        out.append({**doc, "id": item_id})
    return out


def replace_items(container: Any, docs: list[dict], partition_key: str) -> int:
    """Upsert `docs`, then delete every other item in the container; returns how many were deleted.

    Raises UploadFailed, before deleting anything, if any record was rejected. The SDK itself
    retries throttled requests.
    """
    rejected = []
    for doc in docs:
        try:
            container.upsert_item(doc)
        except Exception as exc:  # noqa: BLE001 - collected, then reported together
            rejected.append(f"{doc['id']}: {exc}")
    if rejected:
        raise UploadFailed(f"{len(rejected)} of {len(docs)} records rejected: {rejected[:3]}")

    keep = {doc["id"] for doc in docs}
    query = f"SELECT c.id, c.{partition_key} AS pk FROM c"  # noqa: S608 - field name from UPLOADS
    stale = [
        row
        for row in container.query_items(query=query, enable_cross_partition_query=True)
        if row["id"] not in keep
    ]
    for row in stale:
        container.delete_item(row["id"], partition_key=row["pk"])
    return len(stale)


def upload_to_cosmos(database: Any) -> None:
    for upload in UPLOADS:
        docs = _load_jsonl(DATA_DIR / upload["file"])
        if not docs:
            raise UploadFailed(f"{upload['file']} is missing or empty: generate the data first.")
        container = database.get_container_client(upload["container"])
        print(f"  Uploading {len(docs)} records → {upload['container']}...")
        stale = replace_items(
            container, with_ids(docs, upload["id_field"]), upload["partition_key"]
        )
        print(f"  ✅ {len(docs)} records in {upload['container']}; {stale} stale removed")


def main() -> int:
    # COSMOS_KEY if set, otherwise the caller's Entra ID login (az login), which needs the
    # Cosmos DB data role (infra/populate.py grants it to the operator).
    from argus.config import get_cosmos_database

    print("Uploading synthetic data to Azure Cosmos DB...")
    try:
        upload_to_cosmos(get_cosmos_database())
    except UploadFailed as exc:
        print(f"  ❌ {exc}")
        return 1
    print("\nCosmos DB upload complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
