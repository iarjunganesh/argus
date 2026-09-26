"""
ARGUS — Azure client factories used by the Azure data plane (`argus.data_plane.azure`).
The language model client lives in `argus.models`.
"""

import os

from argus.utils.env_loader import load_repo_env

load_repo_env(__file__)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


# ── Azure Cosmos DB ───────────────────────────────────────────────────────────


def get_cosmos_client():
    endpoint = _require_env("COSMOS_ENDPOINT")
    from azure.cosmos import CosmosClient

    key = os.getenv("COSMOS_KEY")
    if key:
        return CosmosClient(url=endpoint, credential=key)

    from azure.identity import DefaultAzureCredential

    return CosmosClient(
        url=endpoint,
        credential=DefaultAzureCredential(),
    )


def get_cosmos_database():
    return get_cosmos_client().get_database_client(os.environ.get("COSMOS_DATABASE", "argus-db"))


# ── Azure AI Search ───────────────────────────────────────────────────────────


def get_search_client(index_name: str):
    endpoint = _require_env("AZURE_SEARCH_ENDPOINT")
    key = _require_env("AZURE_SEARCH_API_KEY")
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    return SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(key),
    )
