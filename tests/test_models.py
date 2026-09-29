"""The model factory: one setting chooses the provider, and nothing runs without one."""

import pytest

from argus.models import (
    COGNITIVE_SERVICES_SCOPE,
    GITHUB_MODELS_ENDPOINT,
    REASONING_COMPLETION_TOKENS,
    ChatModel,
    ModelUnavailable,
    get_chat_model,
    is_reasoning_model,
)


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
    assert chat.reasoning is True
    assert str(chat.client.base_url) == "https://aoai.example/openai/v1/"
    assert chat.client.api_key == "aoai-test"


async def test_azure_openai_without_a_key_signs_in_with_entra_id(monkeypatch):
    from azure.core.credentials import AccessToken

    scopes = []

    class Credential:
        def get_token(self, *requested, **kwargs):
            scopes.extend(requested)
            return AccessToken("entra-token", 4_102_444_800)

    monkeypatch.setattr("argus.config.get_azure_credential", Credential)
    monkeypatch.setenv("ARGUS_MODEL_PROVIDER", "azure-openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://aoai.example")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini")

    chat = get_chat_model()

    assert chat.client.api_key == ""  # no key: the client asks for a token before each request
    assert await chat.client._refresh_api_key() == "entra-token"
    assert scopes == [COGNITIVE_SERVICES_SCOPE]


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


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("gpt-5.4-mini", True),
        ("GPT-5", True),
        ("openai/gpt-5-mini", True),
        ("o4-mini", True),
        ("o3", True),
        ("gpt-4.1-mini", False),
        ("openai/gpt-4o", False),
        ("my-deployment", False),
    ],
)
def test_reasoning_models_are_recognised_by_name(model, expected):
    assert is_reasoning_model(model) is expected


def test_the_reasoning_setting_overrides_the_name(monkeypatch):
    monkeypatch.setenv("ARGUS_MODEL_REASONING", "True")
    assert is_reasoning_model("my-deployment") is True

    monkeypatch.setenv("ARGUS_MODEL_REASONING", "false")
    assert is_reasoning_model("gpt-5.4-mini") is False

    monkeypatch.setenv("ARGUS_MODEL_REASONING", "maybe")
    with pytest.raises(ModelUnavailable, match="maybe"):
        is_reasoning_model("gpt-5.4-mini")


def test_limits_follow_the_kind_of_model():
    chat = ChatModel("openai", "gpt-4.1-mini", client=None)  # type: ignore[arg-type]
    reasoning = ChatModel("openai", "gpt-5", client=None, reasoning=True)  # type: ignore[arg-type]

    assert chat.limits(max_tokens=250, temperature=0.2) == {"max_tokens": 250, "temperature": 0.2}
    assert reasoning.limits(max_tokens=250, temperature=0.2) == {
        "max_completion_tokens": REASONING_COMPLETION_TOKENS
    }
