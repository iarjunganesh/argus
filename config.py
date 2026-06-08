"""
ARGUS — Shared configuration and Azure client factories.
Supports both GitHub Models (dev) and Azure OpenAI (prod).
"""
import os
from openai import AsyncOpenAI
from utils.env_loader import load_repo_env

load_repo_env(__file__)

USE_GITHUB_MODELS = os.getenv("USE_GITHUB_MODELS", "false").lower() == "true"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} not set — mock fallback will handle")
    return value

# ── OpenAI / GitHub Models client ────────────────────────────────────────────

def get_llm_client() -> AsyncOpenAI:
    """
    Returns AsyncOpenAI client.
    If USE_GITHUB_MODELS=true, points to GitHub Models endpoint.
    Otherwise uses Azure OpenAI.
    """
    if USE_GITHUB_MODELS:
        return AsyncOpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=_require_env("GITHUB_TOKEN"),
        )
    endpoint = _require_env("AZURE_OPENAI_ENDPOINT")
    deployment = _require_env("AZURE_OPENAI_DEPLOYMENT")
    return AsyncOpenAI(
        base_url=f"{endpoint}/openai/deployments/{deployment}",
        api_key=_require_env("AZURE_OPENAI_API_KEY"),
        default_headers={"api-version": os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")},
    )

MODEL_NAME = "gpt-4o"

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
    return get_cosmos_client().get_database_client(
        os.environ.get("COSMOS_DATABASE", "argus-db")
    )

# ── Azure AI Search ───────────────────────────────────────────────────────────

def get_search_client(index_name: str):
    endpoint = _require_env("AZURE_SEARCH_ENDPOINT")
    key = _require_env("AZURE_SEARCH_API_KEY")
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    return SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(key),
    )

# ── Foundry IQ ────────────────────────────────────────────────────────────────

def get_foundry_client():
    """Azure AI Projects client for Foundry IQ knowledge base queries."""
    endpoint = _require_env("FOUNDRY_ENDPOINT")
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
        return AIProjectClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential(),
        )
    except ImportError as exc:
        raise RuntimeError("azure-ai-projects not installed — mock fallback will handle") from exc

FOUNDRY_IQ_KB_REGULATIONS  = os.getenv("FOUNDRY_IQ_KB_REGULATIONS",  "argus-kb-regulations")
FOUNDRY_IQ_KB_SANCTIONS     = os.getenv("FOUNDRY_IQ_KB_SANCTIONS",     "argus-kb-sanctions")
FOUNDRY_IQ_KB_ADVERSEMEDIA  = os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA",  "argus-kb-adversemedia")
