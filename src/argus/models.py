"""The one place ARGUS gets a language model client.

`ARGUS_MODEL_PROVIDER` chooses it:

- `none` (default): no model. Explanations use the fixed template and say so.
- `azure-openai`: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and the deployment name in
  `AZURE_OPENAI_DEPLOYMENT`, through Azure OpenAI's OpenAI-compatible v1 endpoint.
- `openai`: `OPENAI_API_KEY` and the model name in `ARGUS_MODEL`.
- `github-models`: `GITHUB_TOKEN` and the model name in `ARGUS_MODEL`.

A model only ever writes the explanation. Scores, tiers and findings never depend on it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import AsyncOpenAI

PROVIDERS = ("none", "azure-openai", "openai", "github-models")
GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference"


class ModelUnavailable(RuntimeError):
    """No model is configured, or its settings are incomplete."""


@dataclass(frozen=True)
class ChatModel:
    provider: str
    model: str
    client: AsyncOpenAI


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ModelUnavailable(f"{name} is not set")
    return value


def get_chat_model() -> ChatModel:
    provider = os.getenv("ARGUS_MODEL_PROVIDER", "none").strip().lower()
    if provider == "azure-openai":
        endpoint = _require("AZURE_OPENAI_ENDPOINT").rstrip("/")
        client = AsyncOpenAI(
            base_url=f"{endpoint}/openai/v1/", api_key=_require("AZURE_OPENAI_API_KEY")
        )
        return ChatModel(provider, _require("AZURE_OPENAI_DEPLOYMENT"), client)
    if provider == "openai":
        client = AsyncOpenAI(api_key=_require("OPENAI_API_KEY"))
        return ChatModel(provider, _require("ARGUS_MODEL"), client)
    if provider == "github-models":
        client = AsyncOpenAI(base_url=GITHUB_MODELS_ENDPOINT, api_key=_require("GITHUB_TOKEN"))
        return ChatModel(provider, _require("ARGUS_MODEL"), client)
    if provider == "none":
        raise ModelUnavailable("ARGUS_MODEL_PROVIDER is none")
    raise ModelUnavailable(
        f"ARGUS_MODEL_PROVIDER must be one of {', '.join(PROVIDERS)}, not {provider!r}"
    )
