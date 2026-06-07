"""
ARGUS Transaction Intelligence Agent
Analyses synthetic transaction history for AML patterns and typologies.
"""
from fastapi import FastAPI
from utils.structured_logger import get_logger
from pydantic import BaseModel
from agents.transaction.tools.transaction_monitor import transaction_monitor
from agents.transaction.tools.pattern_detector import pattern_detector
from agents.transaction.tools.typology_matcher import typology_matcher
from utils.demo_profiles import get_demo_profile

app = FastAPI(title="ARGUS Transaction Intelligence Agent")
logger = get_logger('agent.transaction')

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
    jurisdiction = p.get("jurisdiction", "")

    if not p.get("include_transaction_analysis", True):
        return {
            "agent": "transaction", "task_id": message.task_id,
            "status": "completed",
            "result": {"skipped": True, "reason": "Transaction analysis disabled for this request"},
        }

    logger.info('invoke', extra={"task_id": message.task_id, "entity": entity_name})
    demo_profile = get_demo_profile(entity_name, entity_type, jurisdiction)
    if demo_profile and demo_profile.get("transaction"):
        return {
            "agent":   "transaction",
            "task_id": message.task_id,
            "status":  "completed",
            "result":  demo_profile["transaction"],
        }

    # Load transaction history
    tx_history = await transaction_monitor(entity_name)

    # Detect statistical anomalies
    patterns = pattern_detector(tx_history)

    # Match against FATF typologies
    typology_hits = await typology_matcher(patterns)

    # Compute transaction risk score
    base_score = 0
    if patterns.get("structuring_flag"):  base_score += 40
    if patterns.get("layering_flag"):     base_score += 30
    if typology_hits:                     base_score += len(typology_hits) * 10
    transaction_risk_score = min(base_score, 100)

    return {
        "agent":   "transaction",
        "task_id": message.task_id,
        "status":  "completed",
        "result": {
            "transaction_count":      tx_history.get("count", 0),
            "date_range":             tx_history.get("date_range", {}),
            "structuring_flag":       patterns.get("structuring_flag", False),
            "layering_flag":          patterns.get("layering_flag", False),
            "anomalous_transactions": patterns.get("flagged_transactions", []),
            "typology_hits":          typology_hits,
            "transaction_risk_score": transaction_risk_score,
        },
    }


@app.get('/health')
def health():
    return {"status": "ok", "service": "transaction", "version": "0.1.0"}
