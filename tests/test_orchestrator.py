"""Orchestrator transport: the A2A envelope sent to each sub-agent."""

import json

import httpx

from argus.agents.orchestrator import agent as orchestrator


async def test_call_agent_posts_envelope_and_returns_json(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"agent": "identity", "status": "completed"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )

    result = await orchestrator.call_agent("identity", {"entity_name": "X"}, "task-1")

    assert result == {"agent": "identity", "status": "completed"}
    assert str(seen[0].url) == f"{orchestrator.AGENT_URLS['identity']}/a2a/invoke"
    body = json.loads(seen[0].content)
    assert body["target_agent"] == "argus-identity-agent-v1"
    assert body["task_id"] == "task-1"
    assert body["payload"] == {"entity_name": "X"}
