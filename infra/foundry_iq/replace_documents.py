"""Make a search index hold exactly a given set of documents.

Used by index_regulations.py and index_sanctions_and_media.py, so rerunning them after the data
is regenerated leaves no stale documents behind, and a document the service rejects stops the run
instead of being counted as indexed.
"""

from __future__ import annotations

from typing import Any

BATCH_SIZE = 100  # well under AI Search's 1000 documents per indexing request


class IndexingFailed(RuntimeError):
    """The service rejected documents; the message names a few of them."""


def replace_documents(client: Any, docs: list[dict], batch_size: int = BATCH_SIZE) -> int:
    """Upload `docs` through a `SearchClient`, then delete every other document in its index.

    Returns how many stale documents were deleted. Raises IndexingFailed, before deleting
    anything, if any upload was rejected.
    """
    rejected = []
    for start in range(0, len(docs), batch_size):
        results = client.upload_documents(docs[start : start + batch_size])
        rejected += [r.key for r in results if not r.succeeded]
    if rejected:
        raise IndexingFailed(f"{len(rejected)} of {len(docs)} documents rejected: {rejected[:5]}")

    keep = {doc["id"] for doc in docs}
    stale = [
        {"id": row["id"]} for row in client.search("*", select=["id"]) if row["id"] not in keep
    ]
    for start in range(0, len(stale), batch_size):
        client.delete_documents(stale[start : start + batch_size])
    return len(stale)
