"""
ARGUS — Azure client factories used by the Azure data plane (`argus.data_plane.azure`).
The language model client lives in `argus.models`.

Cosmos DB, Document Intelligence and Azure OpenAI take a key when one is set and otherwise sign
in with Microsoft Entra ID: the managed identity when deployed, the developer's login locally.
AI Search always takes a key, because the Free tier it runs on has no keyless access.
"""

import os
from functools import cache

from argus.utils.env_loader import load_repo_env

load_repo_env(__file__)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


@cache
def get_azure_credential():
    """The one Entra ID credential, so every client shares its cached tokens."""
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()


# ── Azure Cosmos DB ───────────────────────────────────────────────────────────


def get_cosmos_client():
    endpoint = _require_env("COSMOS_ENDPOINT")
    from azure.cosmos import CosmosClient

    key = os.getenv("COSMOS_KEY")
    if key:
        return CosmosClient(url=endpoint, credential=key)

    return CosmosClient(url=endpoint, credential=get_azure_credential())


def get_cosmos_database():
    return get_cosmos_client().get_database_client(os.environ.get("COSMOS_DATABASE", "argus-db"))


# ── Azure Document Intelligence ───────────────────────────────────────────────


def get_document_intelligence_client():
    endpoint = _require_env("DOC_INTELLIGENCE_ENDPOINT")
    from azure.ai.documentintelligence import DocumentIntelligenceClient

    key = os.getenv("DOC_INTELLIGENCE_KEY")
    if key:
        from azure.core.credentials import AzureKeyCredential

        return DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    return DocumentIntelligenceClient(endpoint=endpoint, credential=get_azure_credential())


# ── Azure AI Search ───────────────────────────────────────────────────────────


def get_knowledge_base_client(knowledge_base_name: str):
    """A Foundry IQ knowledge base on the search service (the stable 2026-04-01 retrieve API)."""
    endpoint = _require_env("AZURE_SEARCH_ENDPOINT")
    key = _require_env("AZURE_SEARCH_API_KEY")
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient

    return KnowledgeBaseRetrievalClient(
        endpoint=endpoint,
        knowledge_base_name=knowledge_base_name,
        credential=AzureKeyCredential(key),
    )
