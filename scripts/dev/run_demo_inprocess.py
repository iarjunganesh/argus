"""Run ARGUS demo in-process by invoking agent `invoke` functions directly.
This avoids network A2A calls and allows a quick end-to-end smoke test.
"""

import asyncio

from argus.agents.orchestrator import agent as orchestrator


async def call_agent_local(agent_name: str, payload: dict, task_id: str) -> dict:
    # Map agent_name to module
    mapping = {
        "identity": "argus.agents.identity.agent",
        "screening": "argus.agents.screening.agent",
        "corporate": "argus.agents.corporate.agent",
        "transaction": "argus.agents.transaction.agent",
        "compliance": "argus.agents.compliance.agent",
    }
    mod_name = mapping.get(agent_name)
    if not mod_name:
        return {"agent": agent_name, "status": "error", "result": None}

    mod = __import__(mod_name, fromlist=["app", "invoke"])
    # Build A2A message using the module's A2AMessage model
    A2A = mod.A2AMessage
    msg = A2A(
        a2a_version="1.0",
        source_agent="argus-demo",
        target_agent=f"argus-{agent_name}",
        task_id=task_id,
        payload=payload,
    )

    res = await mod.invoke(msg)
    # Normalise to expected call_agent shape
    return {
        "agent": agent_name,
        "status": res.get("status", "completed"),
        "result": res.get("result", {}),
    }


async def main():
    # Monkeypatch orchestrator.call_agent in this process
    orchestrator.call_agent = call_agent_local

    # Example KYC request — canonical demo profile key
    kyc = {"entity_name": "Wirecard AG", "entity_type": "corporate", "jurisdiction": "DE"}
    print("Running in-process KYC assessment for:", kyc)
    report = await orchestrator.run_kyc_assessment(kyc)
    import json

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
