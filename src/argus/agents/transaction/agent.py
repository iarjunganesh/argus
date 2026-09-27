"""
ARGUS Transaction Intelligence Agent
Analyses synthetic transaction history for AML patterns and typologies.
"""

from argus.agents.provenance import provenance
from argus.agents.transaction.tools.pattern_detector import pattern_detector
from argus.agents.transaction.tools.transaction_monitor import transaction_monitor
from argus.agents.transaction.tools.typology_matcher import typology_matcher
from argus.utils.structured_logger import get_logger

logger = get_logger("agent.transaction")


async def assess(request: dict, task_id: str) -> dict:
    entity_name = request.get("entity_name", "")

    if not request.get("include_transaction_analysis", True):
        return {
            "agent": "transaction",
            "task_id": task_id,
            "status": "completed",
            **provenance(),
            "result": {"skipped": True, "reason": "Transaction analysis disabled for this request"},
        }

    logger.info("assess", extra={"task_id": task_id, "entity": entity_name})

    # Load transaction history
    tx_history = await transaction_monitor(entity_name)

    # Detect statistical anomalies
    patterns = pattern_detector(tx_history)

    # Match against FATF typologies
    typology = await typology_matcher(patterns)
    typology_hits = typology["hits"]

    # Compute transaction risk score
    base_score = 0
    if patterns.get("structuring_flag"):
        base_score += 40
    if patterns.get("layering_flag"):
        base_score += 30
    if typology_hits:
        base_score += len(typology_hits) * 10
    transaction_risk_score = min(base_score, 100)

    return {
        "agent": "transaction",
        "task_id": task_id,
        "status": "completed",
        **provenance(transaction_monitor=tx_history, typology_matcher=typology),
        "result": {
            "transaction_count": tx_history.get("count", 0),
            "date_range": tx_history.get("date_range", {}),
            "structuring_flag": patterns.get("structuring_flag", False),
            "layering_flag": patterns.get("layering_flag", False),
            "anomalous_transactions": patterns.get("flagged_transactions", []),
            "typology_hits": typology_hits,
            "transaction_risk_score": transaction_risk_score,
        },
    }
