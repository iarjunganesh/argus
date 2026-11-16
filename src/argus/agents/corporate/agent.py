"""
ARGUS Corporate Intelligence Agent
Resolves UBO structure and maps corporate ownership graph.
"""

from argus.agents.compliance.tools.risk_scorer import agent_score
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
    risk_flag_evidence = []
    for node in ubo_result.get("ownership_chain", []):
        node_jrsd = node.get("jurisdiction", "")
        jrsd_info = await jurisdiction_mapper(node_jrsd)
        if jrsd_info.get("fatf_risk_tier") == "high":
            flag = f"High-risk jurisdiction node: {node.get('name')} ({node_jrsd})"
            risk_flags.append(flag)
            risk_flag_evidence.append(
                {
                    "flag": flag,
                    "ownership_node": node,
                    "jurisdiction_assessment": jrsd_info,
                }
            )

    corporate_score = agent_score("corporate", {"risk_flags": risk_flags, "ubo_chain": ubo_result})

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
            "risk_flag_evidence": risk_flag_evidence,
            "corporate_score": corporate_score,
        },
    }
