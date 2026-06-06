"""
ARGUS — Shared configuration and Azure client factories.
Supports both GitHub Models (dev) and Azure OpenAI (prod).
"""
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

USE_GITHUB_MODELS = os.getenv("USE_GITHUB_MODELS", "false").lower() == "true"

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
            api_key=os.environ["GITHUB_TOKEN"],
        )
    return AsyncOpenAI(
        base_url=f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/deployments/{os.environ['AZURE_OPENAI_DEPLOYMENT']}",
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        default_headers={"api-version": os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")},
    )

MODEL_NAME = "gpt-4o"

# ── Azure Cosmos DB ───────────────────────────────────────────────────────────

def get_cosmos_client():
    from azure.cosmos import CosmosClient
    from azure.identity import DefaultAzureCredential
    return CosmosClient(
        url=os.environ["COSMOS_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )

def get_cosmos_database():
    return get_cosmos_client().get_database_client(
        os.environ.get("COSMOS_DATABASE", "argus-db")
    )

# ── Azure AI Search ───────────────────────────────────────────────────────────

def get_search_client(index_name: str):
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    return SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        index_name=index_name,
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_API_KEY"]),
    )

# ── Foundry IQ ────────────────────────────────────────────────────────────────

def get_foundry_client():
    """Azure AI Projects client for Foundry IQ knowledge base queries."""
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
        return AIProjectClient(
            endpoint=os.environ["FOUNDRY_ENDPOINT"],
            credential=DefaultAzureCredential(),
        )
    except ImportError:
        raise ImportError("Install azure-ai-projects: pip install azure-ai-projects")

FOUNDRY_IQ_KB_REGULATIONS  = os.getenv("FOUNDRY_IQ_KB_REGULATIONS",  "argus-kb-regulations")
FOUNDRY_IQ_KB_SANCTIONS     = os.getenv("FOUNDRY_IQ_KB_SANCTIONS",     "argus-kb-sanctions")
FOUNDRY_IQ_KB_ADVERSEMEDIA  = os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA",  "argus-kb-adversemedia")
