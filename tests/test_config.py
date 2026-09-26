"""Azure client factories: which endpoint and credential each one is built with."""

import pytest

import argus.config as config


class Recorder:
    """Stands in for an SDK client class and records how it was constructed."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def test_missing_setting_raises_so_callers_fall_back(monkeypatch):
    monkeypatch.delenv("COSMOS_ENDPOINT", raising=False)

    with pytest.raises(RuntimeError, match="COSMOS_ENDPOINT is not set"):
        config.get_cosmos_client()


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


def test_cosmos_database_name_defaults_and_can_be_set(monkeypatch):
    class Client:
        def get_database_client(self, name):
            return name

    monkeypatch.setattr(config, "get_cosmos_client", Client)
    assert config.get_cosmos_database() == "argus-db"

    monkeypatch.setenv("COSMOS_DATABASE", "other-db")
    assert config.get_cosmos_database() == "other-db"
