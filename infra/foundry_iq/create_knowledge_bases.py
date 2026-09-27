"""
create_knowledge_bases.py
Creates the three Foundry IQ knowledge bases for ARGUS on Azure AI Search.
Run once after Azure resources are provisioned.
Usage: uv run python infra/foundry_iq/create_knowledge_bases.py

For each knowledge base (regulations, sanctions, adverse media) this creates, in order:
  1. the search index (create_search_indexes.py), with the "default" semantic configuration;
  2. a search index knowledge source that returns the fields a citation needs;
  3. the knowledge base itself, with no model: the stable 2026-04-01 API retrieves minimally and
     extractively, which is what the data plane's FoundryIQRetriever asks for.

The names come from `argus.data_plane.azure`, so the runtime and this script always agree.
"""

import os

from argus.data_plane.azure import (
    KNOWLEDGE_BASE_NAMES,
    SOURCE_DATA_FIELDS,
    knowledge_source_name,
)
from argus.utils.env_loader import load_repo_env

load_repo_env(__file__)

DESCRIPTIONS = {
    "regulations": "FATF Recommendations, 4AMLD/6AMLD, GDPR Art. 9, DORA and Wolfsberg texts",
    "sanctions": "Synthetic sanctions data (OFAC/UN/EU/UK schema)",
    "adverse_media": "Synthetic adverse media news corpus",
}


def create_knowledge_bases():
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        KnowledgeBase,
        KnowledgeSourceReference,
        SearchIndexFieldReference,
        SearchIndexKnowledgeSource,
        SearchIndexKnowledgeSourceParameters,
    )

    # Sibling script: the running script's folder is on the import path.
    from create_search_indexes import create_search_indexes

    create_search_indexes()

    client = SearchIndexClient(
        os.environ["AZURE_SEARCH_ENDPOINT"], AzureKeyCredential(os.environ["AZURE_SEARCH_API_KEY"])
    )
    print("Creating Foundry IQ knowledge sources and knowledge bases...")
    for knowledge_base, name in KNOWLEDGE_BASE_NAMES.items():
        source = knowledge_source_name(knowledge_base)
        client.create_or_update_knowledge_source(
            SearchIndexKnowledgeSource(
                name=source,
                description=DESCRIPTIONS[knowledge_base],
                search_index_parameters=SearchIndexKnowledgeSourceParameters(
                    search_index_name=name,
                    semantic_configuration_name="default",
                    source_data_fields=[
                        SearchIndexFieldReference(name=f) for f in SOURCE_DATA_FIELDS
                    ],
                ),
            )
        )
        client.create_or_update_knowledge_base(
            KnowledgeBase(
                name=name,
                description=DESCRIPTIONS[knowledge_base],
                knowledge_sources=[KnowledgeSourceReference(name=source)],
            )
        )
        print(f"  ✅ {knowledge_base}  →  knowledge base: {name}  (source: {source})")

    print("\nAll Foundry IQ knowledge bases ready. Fill the indexes next:")
    print("  uv run python infra/foundry_iq/index_regulations.py")
    print("  uv run python infra/foundry_iq/index_sanctions_and_media.py")


if __name__ == "__main__":
    create_knowledge_bases()
