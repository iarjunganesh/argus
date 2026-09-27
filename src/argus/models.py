"""The one place ARGUS gets a language model client.

`ARGUS_MODEL_PROVIDER` chooses it:

- `none` (default): no model. Explanations use the fixed template and say so.
- `azure-openai`: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and the deployment name in
  `AZURE_OPENAI_DEPLOYMENT`, through Azure OpenAI's OpenAI-compatible v1 endpoint.
- `openai`: `OPENAI_API_KEY` and the model name in `ARGUS_MODEL`.
- `github-models`: `GITHUB_TOKEN` and the model name in `ARGUS_MODEL`.

Reasoning models (the GPT-5 family and the o-series) reject `max_tokens` and `temperature` on the
Chat Completions API and count their hidden reasoning against `max_completion_tokens`.
`ARGUS_MODEL_REASONING` says whether the model is one: `auto` (default) decides from the model
name, `true` or `false` overrides it, for example for an Azure deployment named something else.

A model only ever writes the explanation. Scores, tiers and findings never depend on it.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from openai import AsyncOpenAI

from argus.utils.env_loader import load_repo_env

load_repo_env(__file__)  # the provider settings usually live in the repository's .env

PROVIDERS = ("none", "azure-openai", "openai", "github-models")
GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference"
# A reasoning model's completion budget covers its hidden reasoning as well as the answer.
REASONING_COMPLETION_TOKENS = 4000
# gpt-5*, o1, o3, o4-mini..., optionally behind a publisher prefix such as GitHub Models' "openai/".
_REASONING_NAME = re.compile(r"^(?:[\w.-]+/)?(?:gpt-5|o\d)", re.IGNORECASE)


class ModelUnavailable(RuntimeError):
    """No model is configured, or its settings are incomplete."""


@dataclass(frozen=True)
class ChatModel:
    provider: str
    model: str
    client: AsyncOpenAI
    reasoning: bool = False

    def limits(self, max_tokens: int, temperature: float) -> dict:
        """The length and sampling arguments of a Chat Completions call, as this model takes them.

        A reasoning model gets no temperature (only its default is accepted) and a completion
        budget large enough for its reasoning; the prompt keeps the answer short.
        """
        if self.reasoning:
            return {"max_completion_tokens": REASONING_COMPLETION_TOKENS}
        return {"max_tokens": max_tokens, "temperature": temperature}


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ModelUnavailable(f"{name} is not set")
    return value


def is_reasoning_model(model: str) -> bool:
    setting = os.getenv("ARGUS_MODEL_REASONING", "auto").strip().lower()
    if setting == "auto":
        return bool(_REASONING_NAME.match(model))
    if setting in ("true", "false"):
        return setting == "true"
    raise ModelUnavailable(f"ARGUS_MODEL_REASONING must be auto, true or false, not {setting!r}")


def get_chat_model() -> ChatModel:
    provider = os.getenv("ARGUS_MODEL_PROVIDER", "none").strip().lower()
    if provider == "azure-openai":
        endpoint = _require("AZURE_OPENAI_ENDPOINT").rstrip("/")
        client = AsyncOpenAI(
            base_url=f"{endpoint}/openai/v1/", api_key=_require("AZURE_OPENAI_API_KEY")
        )
        return _chat_model(provider, _require("AZURE_OPENAI_DEPLOYMENT"), client)
    if provider == "openai":
        client = AsyncOpenAI(api_key=_require("OPENAI_API_KEY"))
        return _chat_model(provider, _require("ARGUS_MODEL"), client)
    if provider == "github-models":
        client = AsyncOpenAI(base_url=GITHUB_MODELS_ENDPOINT, api_key=_require("GITHUB_TOKEN"))
        return _chat_model(provider, _require("ARGUS_MODEL"), client)
    if provider == "none":
        raise ModelUnavailable("ARGUS_MODEL_PROVIDER is none")
    raise ModelUnavailable(
        f"ARGUS_MODEL_PROVIDER must be one of {', '.join(PROVIDERS)}, not {provider!r}"
    )


def _chat_model(provider: str, model: str, client: AsyncOpenAI) -> ChatModel:
    return ChatModel(provider, model, client, reasoning=is_reasoning_model(model))
