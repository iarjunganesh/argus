"""
ARGUS Corporate Intelligence Agent
Resolves UBO structure and maps corporate ownership graph.
"""

from argus.agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper
from argus.agents.corporate.tools.registry_lookup import registry_lookup
from argus.agents.corporate.tools.ubo_resolver import ubo_resolver
from argus.agents.provenance import provenance
from argus.utils.structured_logger import get_logger

logger = get_logger("agent.corporate")


async def assess(request: dict, task_id: str) -> dict:
    entity_name = request.get("entity_name", "")
    entity_type = request.get("entity_type", "corporate")
    reg_number = request.get("registration_number")
    jurisdiction = request.get("jurisdiction", "")

    logger.info("assess", extra={"task_id": task_id})

    # Only run UBO resolution for corporate entities
    if entity_type != "corporate":
        return {
            "agent": "corporate",
            "task_id": task_id,
            "status": "completed",
            **provenance(),
            "result": {"skipped": True, "reason": "Entity is individual — UBO not applicable"},
        }

    registry_result = await registry_lookup(entity_name, reg_number)
    ubo_result = await ubo_resolver(entity_name, registry_result)
    jrsd_result = await jurisdiction_mapper(jurisdiction)

    # Identify structural risk flags
    risk_flags = []
    for node in ubo_result.get("ownership_chain", []):
        node_jrsd = node.get("jurisdiction", "")
        jrsd_info = await jurisdiction_mapper(node_jrsd)
        if jrsd_info.get("fatf_risk_tier") == "high":
            risk_flags.append(f"High-risk jurisdiction node: {node.get('name')} ({node_jrsd})")

    corporate_score = 100
    if risk_flags:
        corporate_score -= len(risk_flags) * 15
    if ubo_result.get("depth", 0) > 3:
        corporate_score -= 10
    corporate_score = max(0, corporate_score)

    return {
        "agent": "corporate",
        "task_id": task_id,
        "status": "completed",
        **provenance(registry_lookup=registry_result, ubo_resolver=ubo_result),
        "result": {
            "registry": registry_result,
            "ubo_chain": ubo_result,
            "jurisdiction_info": jrsd_result,
            "risk_flags": risk_flags,
            "corporate_score": corporate_score,
        },
    }
