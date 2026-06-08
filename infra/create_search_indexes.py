"""
create_search_indexes.py
Creates the three Azure AI Search indexes that back the Foundry IQ knowledge bases.

  KB-Regulations  → argus-kb-regulations  (FATF / 4AMLD / 6AMLD / GDPR)
  KB-Sanctions    → argus-kb-sanctions    (synthetic OFAC/UN/EU/UK data)
  KB-AdverseMedia → argus-kb-adversemedia (synthetic news corpus)

These indexes are the Foundry IQ intelligence layer for ARGUS.
Run after Azure AI Search is provisioned.
Usage: python infra/create_search_indexes.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.env_loader import load_repo_env

load_repo_env(__file__)

# Index names (mapped from KB env vars)
INDEXES = {
    "argus-kb-regulations":  os.getenv("FOUNDRY_IQ_KB_REGULATIONS",  "argus-kb-regulations"),
    "argus-kb-sanctions":    os.getenv("FOUNDRY_IQ_KB_SANCTIONS",     "argus-kb-sanctions"),
    "argus-kb-adversemedia": os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA",  "argus-kb-adversemedia"),
}


def _build_index_payload(name: str) -> dict:
    return {
        "name": name,
        "fields": [
            {
                "name": "id",
                "type": "Edm.String",
                "key": True,
                "filterable": True,
            },
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": True,
                "analyzer": "standard.lucene",
            },
            {
                "name": "title",
                "type": "Edm.String",
                "searchable": True,
                "filterable": True,
            },
            {
                "name": "entity_name",
                "type": "Edm.String",
                "searchable": True,
                "filterable": True,
            },
            {
                "name": "source_doc",
                "type": "Edm.String",
                "filterable": True,
                "retrievable": True,
            },
            {
                "name": "category",
                "type": "Edm.String",
                "filterable": True,
                "retrievable": True,
            },
            {
                "name": "metadata_json",
                "type": "Edm.String",
                "retrievable": True,
            },
        ],
    }


def _create_indexes_via_rest(endpoint: str, key: str) -> None:
    import urllib.request

    endpoint = endpoint.rstrip("/")
    print("Creating Foundry IQ knowledge base indexes in Azure AI Search via REST...")
    for logical_name, index_name in INDEXES.items():
        payload = _build_index_payload(index_name)
        request = urllib.request.Request(
            f"{endpoint}/indexes/{index_name}?api-version=2023-11-01",
            data=json.dumps(payload).encode("utf-8"),
            method="PUT",
            headers={
                "Content-Type": "application/json",
                "api-key": key,
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            response.read()
        print(f"  ✅ {logical_name}  →  index: {index_name}")


def create_search_indexes():
    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key      = os.environ["AZURE_SEARCH_API_KEY"]
    try:
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import (
            SearchIndex,
            SimpleField,
            SearchableField,
            SearchFieldDataType,
            SemanticConfiguration,
            SemanticSearch,
            SemanticPrioritizedFields,
            SemanticField,
        )
        from azure.core.credentials import AzureKeyCredential

        print("Creating Foundry IQ knowledge base indexes in Azure AI Search...")

        client = SearchIndexClient(endpoint, AzureKeyCredential(key))

        for logical_name, index_name in INDEXES.items():
            try:
                index = SearchIndex(
                    name=index_name,
                    fields=[
                        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
                        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
                        SearchableField(name="title", type=SearchFieldDataType.String, filterable=True),
                        SearchableField(name="entity_name", type=SearchFieldDataType.String, filterable=True),
                        SimpleField(name="source_doc", type=SearchFieldDataType.String, filterable=True, retrievable=True),
                        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, retrievable=True),
                        SimpleField(name="metadata_json", type=SearchFieldDataType.String, retrievable=True),
                    ],
                    semantic_search=SemanticSearch(configurations=[
                        SemanticConfiguration(
                            name="default",
                            prioritized_fields=SemanticPrioritizedFields(
                                title_field=SemanticField(field_name="title"),
                                content_fields=[SemanticField(field_name="content")],
                                keywords_fields=[SemanticField(field_name="entity_name")],
                            ),
                        )
                    ]),
                )
                client.create_or_update_index(index)
                print(f"  ✅ {logical_name}  →  index: {index_name}")
            except Exception as e:
                print(f"  ❌ Failed to create {index_name}: {e}")
                raise

    except ImportError:
        _create_indexes_via_rest(endpoint, key)

    print(f"\nFoundry IQ indexes ready. Run 'make index-knowledge-bases' to populate them.")


if __name__ == "__main__":
    create_search_indexes()
