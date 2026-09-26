"""Client factories: which endpoint and credential each one is built with."""

import sys

import pytest

import argus.config as config


class Recorder:
    """Stands in for an SDK client class and records how it was constructed."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def test_missing_setting_raises_so_callers_fall_back(monkeypatch):
    monkeypatch.delenv("COSMOS_ENDPOINT", raising=False)

    with pytest.raises(RuntimeError, match="COSMOS_ENDPOINT not set"):
        config.get_cosmos_client()


def test_llm_client_for_github_models(monkeypatch):
    monkeypatch.setattr(config, "USE_GITHUB_MODELS", True)
    monkeypatch.setenv("GITHUB_TOKEN", "gh-test")

    client = config.get_llm_client()

    assert str(client.base_url).startswith("https://models.inference.ai.azure.com")
    assert client.api_key == "gh-test"


def test_llm_client_for_azure_openai(monkeypatch):
    monkeypatch.setattr(config, "USE_GITHUB_MODELS", False)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://aoai.example")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "aoai-test")

    client = config.get_llm_client()

    assert str(client.base_url) == "https://aoai.example/openai/deployments/gpt-4o/"
    assert client.default_headers["api-version"] == "2025-01-01-preview"


def test_cosmos_uses_key_when_given(monkeypatch):
    monkeypatch.setattr("azure.cosmos.CosmosClient", Recorder)
    monkeypatch.setenv("COSMOS_ENDPOINT", "https://cosmos.example")
    monkeypatch.setenv("COSMOS_KEY", "cosmos-test")

    client = config.get_cosmos_client()

    assert client.kwargs == {"url": "https://cosmos.example", "credential": "cosmos-test"}


def test_cosmos_uses_entra_id_without_key(monkeypatch):
    monkeypatch.setattr("azure.cosmos.CosmosClient", Recorder)
    monkeypatch.setattr("azure.identity.DefaultAzureCredential", Recorder)
    monkeypatch.setenv("COSMOS_ENDPOINT", "https://cosmos.example")
    monkeypatch.delenv("COSMOS_KEY", raising=False)

    client = config.get_cosmos_client()

    assert isinstance(client.kwargs["credential"], Recorder)


def test_search_client(monkeypatch):
    monkeypatch.setattr("azure.search.documents.SearchClient", Recorder)
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://search.example")
    monkeypatch.setenv("AZURE_SEARCH_API_KEY", "search-test")

    client = config.get_search_client("idx")

    assert client.kwargs["endpoint"] == "https://search.example"
    assert client.kwargs["index_name"] == "idx"
    assert client.kwargs["credential"].key == "search-test"


def test_foundry_client(monkeypatch):
    monkeypatch.setattr("azure.ai.projects.AIProjectClient", Recorder)
    monkeypatch.setattr("azure.identity.DefaultAzureCredential", Recorder)
    monkeypatch.setenv("FOUNDRY_ENDPOINT", "https://foundry.example")

    client = config.get_foundry_client()

    assert client.kwargs["endpoint"] == "https://foundry.example"


def test_foundry_client_without_sdk_raises_runtime_error(monkeypatch):
    monkeypatch.setenv("FOUNDRY_ENDPOINT", "https://foundry.example")
    monkeypatch.setitem(sys.modules, "azure.ai.projects", None)

    with pytest.raises(RuntimeError, match="azure-ai-projects not installed"):
        config.get_foundry_client()
