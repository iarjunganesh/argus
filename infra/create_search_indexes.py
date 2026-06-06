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
import os
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)
from azure.core.credentials import AzureKeyCredential

load_dotenv()

# Index names (mapped from KB env vars)
INDEXES = {
    "argus-kb-regulations":  os.getenv("FOUNDRY_IQ_KB_REGULATIONS",  "argus-kb-regulations"),
    "argus-kb-sanctions":    os.getenv("FOUNDRY_IQ_KB_SANCTIONS",     "argus-kb-sanctions"),
    "argus-kb-adversemedia": os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA",  "argus-kb-adversemedia"),
}


def _build_index(name: str) -> SearchIndex:
    """Build the common schema used across all three Foundry IQ indexes."""
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            analyzer_name="standard.lucene",
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="entity_name",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="source_doc",
            type=SearchFieldDataType.String,
            filterable=True,
            retrievable=True,
        ),
        SimpleField(
            name="category",
            type=SearchFieldDataType.String,
            filterable=True,
            retrievable=True,
        ),
        SimpleField(
            name="metadata_json",
            type=SearchFieldDataType.String,
            retrievable=True,
        ),
    ]

    semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[SemanticField(field_name="entity_name")],
        ),
    )

    return SearchIndex(
        name=name,
        fields=fields,
        semantic_search=SemanticSearch(configurations=[semantic_config]),
    )


def create_search_indexes():
    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key      = os.environ["AZURE_SEARCH_API_KEY"]
    client   = SearchIndexClient(endpoint, AzureKeyCredential(key))

    print("Creating Foundry IQ knowledge base indexes in Azure AI Search...")

    for logical_name, index_name in INDEXES.items():
        try:
            index = _build_index(index_name)
            client.create_or_update_index(index)
            print(f"  ✅ {logical_name}  →  index: {index_name}")
        except Exception as e:
            print(f"  ❌ Failed to create {index_name}: {e}")
            raise

    print(f"\nFoundry IQ indexes ready. Run 'make index-knowledge-bases' to populate them.")


if __name__ == "__main__":
    create_search_indexes()
