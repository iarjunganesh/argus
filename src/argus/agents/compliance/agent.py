"""
ARGUS Compliance & Risk Agent
Fan-in agent — receives all upstream results, searches the regulations knowledge base for
regulatory text with citations, produces final weighted risk score. A potential sanctions match
holds the case whatever the score, and a case whose sanctions screening did not run is reported
as incomplete. A PEP match requires enhanced due diligence whatever the tier.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from argus.agents.compliance.tools.explain_decision import explain_decision
from argus.agents.compliance.tools.gap_analyzer import gap_analyzer
from argus.agents.compliance.tools.regulations_rag import regulations_rag
from argus.agents.compliance.tools.risk_scorer import risk_scorer, score_tier
from argus.agents.provenance import provenance
from argus.utils.structured_logger import get_logger

app = FastAPI(title="ARGUS Compliance & Risk Agent")
logger = get_logger("agent.compliance")

# What sanctions screening established for the case (`risk_summary.sanctions_screening`).
POTENTIAL_MATCH = "potential_match"
NO_MATCH = "no_match"
NOT_RUN = "not_run"


class A2AMessage(BaseModel):
    a2a_version: str
    source_agent: str
    target_agent: str
    task_id: str
    payload: dict


@app.post("/a2a/invoke")
async def invoke(message: A2AMessage):
    p = message.payload
    jurisdiction = p.get("jurisdiction", "")
    entity_type = p.get("entity_type", "corporate")
    upstream = p.get("upstream_results", {})

    identity = upstream.get("identity", {}).get("result") or {}
    screening = upstream.get("screening", {}).get("result") or {}
    corporate = upstream.get("corporate", {}).get("result") or {}
    transaction = upstream.get("transaction", {}).get("result") or {}

    logger.info("invoke", extra={"task_id": message.task_id, "jurisdiction": jurisdiction})
    sanctions = sanctions_screening(upstream.get("screening", {}))

    # Build risk indicator list from upstream findings
    risk_indicators = []
    if screening.get("pep_hit"):
        risk_indicators.append("pep")
    if sanctions == POTENTIAL_MATCH:
        risk_indicators.append("sanctions")
    elif sanctions == NOT_RUN:
        risk_indicators.append("sanctions_not_screened")
    if screening.get("adverse_media_hit"):
        risk_indicators.append("adverse_media")
    if corporate.get("risk_flags"):
        risk_indicators.extend(["high_risk_jurisdiction"])
    if transaction.get("structuring_flag"):
        risk_indicators.append("structuring")

    # Search the regulations knowledge base for applicable rules (cited)
    reg_query = f"KYC AML obligations for {entity_type} entities"
    if risk_indicators:
        reg_query += f" with {', '.join(risk_indicators)} indicators"
    regulations = await regulations_rag(reg_query, jurisdiction, entity_type, risk_indicators)

    # Compute weighted risk score
    scores = risk_scorer(identity, screening, corporate, transaction)

    # Identify compliance gaps
    gaps = gap_analyzer(risk_indicators, regulations, scores)

    # The tier comes from the score band, except that a potential sanctions match holds the case
    # at CRITICAL whatever the score: sanctions are not weighed against other risk (FATF R.6).
    overall_score = scores["overall"]
    tier, tier_basis = score_tier(overall_score), "score"
    if sanctions == POTENTIAL_MATCH:
        tier, tier_basis = "CRITICAL", "sanctions_match"

    key_findings = _extract_findings(identity, screening, corporate, transaction, sanctions)

    regulatory_triggers = [
        {
            "rule": r.get("text", "")[:120],
            "citation": r.get("citation"),
        }
        for r in regulations.get("regulations", [])[:4]
    ]

    recommended_actions = _build_actions(tier, risk_indicators, gaps)
    # A PEP match requires enhanced due diligence measures, not a higher risk tier: the EU AMLR
    # (Art. 42) and UK MLR (reg. 35) apply them to every PEP, FATF R.12 to every foreign PEP.
    # ARGUS cannot yet tell foreign from domestic PEPs, so it applies the all-PEP rule.
    edd_required = "pep" in risk_indicators
    risk_summary = {
        "overall_risk_tier": tier,
        "overall_risk_score": overall_score,
        "tier_basis": tier_basis,
        "sanctions_screening": sanctions,
        "edd_required": edd_required,
        "decision_recommendation": _recommendation(tier, sanctions, edd_required),
    }
    explanation = await explain_decision(
        entity={
            "name": p.get("entity_name", "Unknown"),
            "type": entity_type,
            "jurisdiction": jurisdiction,
        },
        risk_summary=risk_summary,
        dimension_scores=scores["dimensions"],
        key_findings=key_findings,
        regulatory_triggers=regulatory_triggers,
    )

    return {
        "agent": "compliance",
        "task_id": message.task_id,
        "status": "completed",
        **provenance(regulations_rag=regulations),
        "result": {
            "explanation": explanation["text"],
            "explanation_source": explanation["source"],
            "risk_summary": risk_summary,
            "dimension_scores": scores["dimensions"],
            "key_findings": key_findings,
            "regulatory_triggers": regulatory_triggers,
            "recommended_actions": recommended_actions,
            "compliance_gaps": gaps,
            "retrieval_queries": int(regulations.get("source") != "fallback"),
        },
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "compliance", "version": "0.1.0"}


def sanctions_screening(screening_response: dict) -> str:
    """What sanctions screening established: a potential match, no match, or nothing.

    Screening that did not run (the agent failed, or the sanctions search fell back) is not the
    same as no match: the case cannot be cleared without it.
    """
    result = screening_response.get("result") or {}
    if not result or "sanctions_checker" in screening_response.get("fallbacks", []):
        return NOT_RUN
    return POTENTIAL_MATCH if result.get("sanctions_hit") else NO_MATCH


def _extract_findings(identity, screening, corporate, transaction, sanctions: str) -> list:
    _ = identity
    findings: list[str] = []
    if screening.get("pep_hit"):
        findings.extend(
            f"PEP identified: {f.get('match', '')[:100]}"
            for f in screening.get("findings", [])
            if f.get("type") == "pep"
        )
    if screening.get("adverse_media_hit"):
        findings.append("Adverse media coverage found — review required")
    if sanctions == POTENTIAL_MATCH:
        findings.append("⚠️ Potential sanctions match: a person must confirm or clear it")
    elif sanctions == NOT_RUN:
        findings.append("⚠️ Sanctions screening did not run")
    findings.extend(corporate.get("risk_flags") or [])
    if transaction.get("structuring_flag"):
        findings.append("Transaction structuring pattern detected")
    if not findings:
        findings.append("No high-risk indicators found across all screening dimensions")
    return findings


def _recommendation(tier: str, sanctions: str = NO_MATCH, edd_required: bool = False) -> str:
    if sanctions == POTENTIAL_MATCH:
        return (
            "Hold: do not onboard or process transactions until a compliance officer confirms "
            "or clears the potential sanctions match."
        )
    if sanctions == NOT_RUN:
        return "Incomplete: sanctions screening did not run. Do not onboard until it has."
    if edd_required and tier != "CRITICAL":
        return (
            "Enhanced Due Diligence required before onboarding: a PEP match needs senior "
            "management approval, source of wealth and funds, and enhanced ongoing monitoring."
        )
    return {
        "LOW": "Standard onboarding — periodic review recommended.",
        "MEDIUM": "Proceed with caution. Enhanced monitoring required.",
        "HIGH": "Enhanced Due Diligence required before onboarding.",
        "CRITICAL": "Do not onboard. Escalate to Senior Compliance Officer immediately.",
    }.get(tier, "Review required.")


def _build_actions(tier: str, risk_indicators: list, gaps: list) -> list:
    actions = []
    if "pep" in risk_indicators:
        actions.append("Obtain source of wealth and source of funds declaration")
        actions.append("Escalate to Senior Compliance Officer for EDD sign-off")
        actions.append("Apply enhanced ongoing monitoring to the relationship")
    if "sanctions" in risk_indicators:
        actions.append(
            "Confirm or clear the match: compare the listing's identifiers (date of birth, "
            "nationality, registration number) with the customer's"
        )
        actions.append(
            "If confirmed: freeze funds without delay and report the frozen assets to the "
            "competent authority (FATF R.6)"
        )
    if "sanctions_not_screened" in risk_indicators:
        actions.append("Run sanctions screening before any onboarding decision")
    if "high_risk_jurisdiction" in risk_indicators:
        actions.append("Obtain beneficial owner register for all offshore entities")
    if "structuring" in risk_indicators:
        actions.append("Consider filing Suspicious Activity Report (SAR)")
    if tier in ("HIGH", "CRITICAL"):
        actions.append("Conduct in-person verification or enhanced video KYC")
    actions.extend(gaps[:2])
    return actions or ["Continue standard periodic review cycle"]
