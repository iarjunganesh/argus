"""Compliance: evaluate canonical findings, retrieve citations, then explain the recommendation."""

import re

from argus.agents.compliance.tools.explain_decision import explain_decision
from argus.agents.compliance.tools.regulations_rag import regulations_rag
from argus.agents.provenance import provenance
from argus.decision import evaluate_decision, risk_indicators
from argus.findings import collect_findings, key_findings
from argus.utils.structured_logger import get_logger

logger = get_logger("agent.compliance")

# A regulatory trigger retains the first sentence and cites the full document.
RULE_MAX_CHARS = 300
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def rule_statement(text: str, limit: int = RULE_MAX_CHARS) -> str:
    """The passage's first sentence; if longer than `limit`, cut at a word and marked with …"""
    sentence = _SENTENCE_END.split(text.strip(), maxsplit=1)[0]
    if len(sentence) <= limit:
        return sentence
    return sentence[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


async def assess(request: dict, task_id: str) -> dict:
    jurisdiction = request.get("jurisdiction", "")
    entity_type = request.get("entity_type", "corporate")
    logger.info("assess", extra={"task_id": task_id, "jurisdiction": jurisdiction})
    records = collect_findings(request.get("upstream_results", {}))
    decision = evaluate_decision(records.findings)
    indicators = risk_indicators(records.findings)

    reg_query = f"KYC AML obligations for {entity_type} entities"
    if indicators:
        reg_query += f" with {', '.join(indicators)} indicators"
    regulations = await regulations_rag(reg_query, jurisdiction, entity_type, indicators)
    triggers = [
        {"rule": rule_statement(r.get("text", "")), "citation": r.get("citation")}
        for r in regulations.get("regulations", [])[:4]
    ]
    display_findings = key_findings(records.findings)
    explanation = await explain_decision(
        entity={
            "name": request.get("entity_name", "Unknown"),
            "type": entity_type,
            "jurisdiction": jurisdiction,
        },
        risk_summary=decision.risk_summary,
        dimension_scores=decision.dimension_scores,
        key_findings=display_findings,
        regulatory_triggers=triggers,
    )
    canonical = records.model_dump(mode="json")
    return {
        "agent": "compliance",
        "task_id": task_id,
        "status": "completed",
        **provenance(regulations_rag=regulations),
        "result": {
            "explanation": explanation["text"],
            "explanation_source": explanation["source"],
            "risk_summary": decision.risk_summary,
            "dimension_scores": decision.dimension_scores,
            "key_findings": display_findings,
            **canonical,
            "decision_record": decision.model_dump(mode="json"),
            "regulatory_triggers": triggers,
            "recommended_actions": list(decision.recommended_actions),
            "compliance_gaps": list(decision.obligations),
            "retrieval_queries": int(regulations.get("source") != "fallback"),
        },
    }
