"""
index_regulations.py
Indexes public regulatory text (FATF/4AMLD/6AMLD) into Foundry IQ KB-Regulations.
Source files should be placed in data/public/ before running.
"""

import json
import os
from pathlib import Path

from replace_documents import replace_documents

from argus.data_plane.corpus import regulation_documents
from argus.utils.env_loader import load_repo_env

load_repo_env(__file__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "public"
KB_NAME = os.getenv("FOUNDRY_IQ_KB_REGULATIONS", "argus-kb-regulations")


def index_regulations():
    print(f"Indexing regulatory text into Foundry IQ {KB_NAME}...")

    # If no files in data/public, use embedded regulation documents above
    txt_files = list(DATA_DIR.glob("*.txt")) + list(DATA_DIR.glob("*.pdf"))
    if txt_files:
        print(f"  Found {len(txt_files)} documents in {DATA_DIR} — loading from files.")
    else:
        print(f"  No files in {DATA_DIR} — using embedded FATF/4AMLD/6AMLD/GDPR/DORA text.")

    docs_to_index = regulation_documents()  # the same corpus the local retriever searches

    # Optionally load from txt files too
    for txt_file in txt_files:
        content = txt_file.read_text(encoding="utf-8", errors="ignore")
        docs_to_index.append(
            {
                "id": txt_file.stem,
                "title": txt_file.stem.replace("-", " ").replace("_", " ").title(),
                "source_doc": txt_file.name,
                "category": "regulation",
                "content": content[:5000],
                "entity_name": "",
                "metadata_json": json.dumps({"file": txt_file.name}),
            }
        )

    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key = os.environ["AZURE_SEARCH_API_KEY"]
    client = SearchClient(endpoint, KB_NAME, AzureKeyCredential(key))
    stale = replace_documents(client, docs_to_index)
    print(
        f"  ✅ {len(docs_to_index)} regulation documents indexed into {KB_NAME}; {stale} stale removed"
    )


if __name__ == "__main__":
    index_regulations()
