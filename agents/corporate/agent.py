"""
ARGUS Corporate Intelligence Agent
Resolves UBO structure and maps corporate ownership graph.
"""
from fastapi import FastAPI
from utils.structured_logger import get_logger
from pydantic import BaseModel
from agents.corporate.tools.ubo_resolver import ubo_resolver
from agents.corporate.tools.registry_lookup import registry_lookup
from agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper

app = FastAPI(title="ARGUS Corporate Intelligence Agent")
logger = get_logger('agent.corporate')

class A2AMessage(BaseModel):
    a2a_version: str
    source_agent: str
    target_agent: str
    task_id: str
    payload: dict

@app.post("/a2a/invoke")
async def invoke(message: A2AMessage):
    p           = message.payload
    entity_name = p.get("entity_name", "")
    entity_type = p.get("entity_type", "corporate")
    reg_number  = p.get("registration_number")
    jurisdiction= p.get("jurisdiction", "")

    logger.info('invoke', extra={"task_id": message.task_id, "entity": entity_name})
    # Only run UBO resolution for corporate entities
    if entity_type != "corporate":
        return {
            "agent":   "corporate",
            "task_id": message.task_id,
            "status":  "completed",
            "result":  {"skipped": True, "reason": "Entity is individual — UBO not applicable"},
        }

    registry_result  = await registry_lookup(entity_name, reg_number)
    ubo_result       = await ubo_resolver(entity_name, registry_result)
    jrsd_result      = await jurisdiction_mapper(jurisdiction)

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
        "agent":   "corporate",
        "task_id": message.task_id,
        "status":  "completed",
        "result": {
            "registry":         registry_result,
            "ubo_chain":        ubo_result,
            "jurisdiction_info":jrsd_result,
            "risk_flags":       risk_flags,
            "corporate_score":  corporate_score,
        },
    }


@app.get('/health')
def health():
    return {"status": "ok", "service": "corporate", "version": "0.1.0"}
