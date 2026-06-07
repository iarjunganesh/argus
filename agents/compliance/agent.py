"""
ARGUS Compliance & Risk Agent
Fan-in agent — receives all upstream results, queries Foundry IQ for
regulatory text with citations, produces final weighted risk score.
"""
from fastapi import FastAPI
from utils.structured_logger import get_logger
from pydantic import BaseModel
from agents.compliance.tools.explain_decision import explain_decision
from agents.compliance.tools.regulations_rag import regulations_rag
from agents.compliance.tools.risk_scorer import risk_scorer
from agents.compliance.tools.gap_analyzer import gap_analyzer

app = FastAPI(title="ARGUS Compliance & Risk Agent")
logger = get_logger('agent.compliance')

class A2AMessage(BaseModel):
    a2a_version: str
    source_agent: str
    target_agent: str
    task_id: str
    payload: dict

@app.post("/a2a/invoke")
async def invoke(message: A2AMessage):
    p           = message.payload
    jurisdiction= p.get("jurisdiction", "")
    entity_type = p.get("entity_type", "corporate")
    upstream    = p.get("upstream_results", {})

    identity    = upstream.get("identity",    {}).get("result") or {}
    screening   = upstream.get("screening",   {}).get("result") or {}
    corporate   = upstream.get("corporate",   {}).get("result") or {}
    transaction = upstream.get("transaction", {}).get("result") or {}

    logger.info('invoke', extra={"task_id": message.task_id, "jurisdiction": jurisdiction})
    # Build risk indicator list from upstream findings
    risk_indicators = []
    if screening.get("pep_hit"):            risk_indicators.append("pep")
    if screening.get("sanctions_hit"):      risk_indicators.append("sanctions")
    if screening.get("adverse_media_hit"):  risk_indicators.append("adverse_media")
    if corporate.get("risk_flags"):         risk_indicators.extend(["high_risk_jurisdiction"])
    if transaction.get("structuring_flag"): risk_indicators.append("structuring")

    # Query Foundry IQ for applicable regulations (cited)
    reg_query = f"KYC AML obligations for {entity_type} entities"
    if risk_indicators:
        reg_query += f" with {', '.join(risk_indicators)} indicators"
    regulations = await regulations_rag(reg_query, jurisdiction, entity_type, risk_indicators)

    # Compute weighted risk score
    scores = risk_scorer(identity, screening, corporate, transaction)

    # Identify compliance gaps
    gaps = gap_analyzer(risk_indicators, regulations, scores)

    # Build risk summary
    overall_score = scores["overall"]
    if overall_score >= 75:   tier = "CRITICAL"
    elif overall_score >= 55: tier = "HIGH"
    elif overall_score >= 35: tier = "MEDIUM"
    else:                     tier = "LOW"

    key_findings = _extract_findings(identity, screening, corporate, transaction)

    regulatory_triggers = [
        {
            "rule":               r.get("text", "")[:120],
            "foundry_iq_citation":r.get("foundry_iq_citation"),
        }
        for r in regulations.get("regulations", [])[:4]
    ]

    recommended_actions = _build_actions(tier, risk_indicators, gaps)
    explanation = await explain_decision(
        entity={
            "name": p.get("entity_name", "Unknown"),
            "type": entity_type,
            "jurisdiction": jurisdiction,
        },
        risk_summary={
            "overall_risk_tier": tier,
            "overall_risk_score": overall_score,
        },
        dimension_scores=scores["dimensions"],
        key_findings=key_findings,
        regulatory_triggers=regulatory_triggers,
    )

    return {
        "agent":   "compliance",
        "task_id": message.task_id,
        "status":  "completed",
        "result": {
            "explanation": explanation,
            "risk_summary": {
                "overall_risk_tier":     tier,
                "overall_risk_score":    overall_score,
                "confidence":            round(scores.get("confidence", 0.8), 2),
                "decision_recommendation": _recommendation(tier),
            },
            "dimension_scores":    scores["dimensions"],
            "key_findings":        key_findings,
            "regulatory_triggers": regulatory_triggers,
            "recommended_actions": recommended_actions,
            "compliance_gaps":     gaps,
            "foundry_iq_queries":  1,
        },
    }


@app.get('/health')
def health():
    return {"status": "ok", "service": "compliance", "version": "0.1.0"}


def _extract_findings(identity, screening, corporate, transaction) -> list:
    _ = identity
    findings = []
    if screening.get("pep_hit"):
        for f in screening.get("findings", []):
            if f.get("type") == "pep":
                findings.append(f"PEP identified: {f.get('match','')[:100]}")
    if screening.get("adverse_media_hit"):
        findings.append("Adverse media coverage found — review required")
    if screening.get("sanctions_hit"):
        findings.append("⚠️ Sanctions match detected")
    for flag in (corporate.get("risk_flags") or []):
        findings.append(flag)
    if transaction.get("structuring_flag"):
        findings.append("Transaction structuring pattern detected")
    if not findings:
        findings.append("No high-risk indicators found across all screening dimensions")
    return findings


def _recommendation(tier: str) -> str:
    return {
        "LOW":      "Standard onboarding — periodic review recommended.",
        "MEDIUM":   "Proceed with caution. Enhanced monitoring required.",
        "HIGH":     "Enhanced Due Diligence required before onboarding.",
        "CRITICAL": "Do not onboard. Escalate to Senior Compliance Officer immediately.",
    }.get(tier, "Review required.")


def _build_actions(tier: str, risk_indicators: list, gaps: list) -> list:
    actions = []
    if "pep" in risk_indicators:
        actions.append("Obtain source of wealth and source of funds declaration")
        actions.append("Escalate to Senior Compliance Officer for EDD sign-off")
    if "sanctions" in risk_indicators:
        actions.append("Immediately escalate — do not proceed with onboarding")
        actions.append("Notify Compliance Officer and legal team")
    if "high_risk_jurisdiction" in risk_indicators:
        actions.append("Obtain beneficial owner register for all offshore entities")
    if "structuring" in risk_indicators:
        actions.append("Consider filing Suspicious Activity Report (SAR)")
    if tier in ("HIGH", "CRITICAL"):
        actions.append("Conduct in-person verification or enhanced video KYC")
    actions.extend(gaps[:2])
    return actions or ["Continue standard periodic review cycle"]
