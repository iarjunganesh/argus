"""The model factory: one setting chooses the provider, and nothing runs without one."""

import pytest

from argus.models import GITHUB_MODELS_ENDPOINT, ModelUnavailable, get_chat_model


def test_no_provider_means_no_model():
    with pytest.raises(ModelUnavailable, match="none"):
        get_chat_model()


def test_unknown_provider_is_named(monkeypatch):
    monkeypatch.setenv("ARGUS_MODEL_PROVIDER", "carrier-pigeon")

    with pytest.raises(ModelUnavailable, match="carrier-pigeon"):
        get_chat_model()


def test_azure_openai_uses_the_v1_endpoint_and_deployment(monkeypatch):
    monkeypatch.setenv("ARGUS_MODEL_PROVIDER", "Azure-OpenAI")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://aoai.example/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "aoai-test")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini")

    chat = get_chat_model()

    assert chat.provider == "azure-openai" and chat.model == "gpt-5.4-mini"
    assert str(chat.client.base_url) == "https://aoai.example/openai/v1/"
    assert chat.client.api_key == "aoai-test"


def test_openai_needs_a_model_name(monkeypatch):
    monkeypatch.setenv("ARGUS_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with pytest.raises(ModelUnavailable, match="ARGUS_MODEL"):
        get_chat_model()

    monkeypatch.setenv("ARGUS_MODEL", "some-model")
    assert get_chat_model().model == "some-model"


def test_github_models(monkeypatch):
    monkeypatch.setenv("ARGUS_MODEL_PROVIDER", "github-models")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-test")
    monkeypatch.setenv("ARGUS_MODEL", "openai/some-model")

    chat = get_chat_model()

    assert str(chat.client.base_url).startswith(GITHUB_MODELS_ENDPOINT)
    assert chat.client.api_key == "gh-test"
