"""A machine recommendation against one finding set, awaiting a separate human decision."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from argus.agents.compliance.tools.gap_analyzer import gap_analyzer
from argus.agents.compliance.tools.risk_scorer import risk_scorer, score_tier
from argus.findings import POLICY_VERSION, Finding

POTENTIAL_MATCH = "potential_match"
NO_MATCH = "no_match"
NOT_RUN = "not_run"


class DecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_version: Literal["argus-risk-v1"] = POLICY_VERSION
    # These are evaluated policy inputs, not a minimal sufficient set or additive attribution.
    finding_ids: tuple[str, ...]
    risk_summary: dict
    dimension_scores: dict
    obligations: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    evaluated_at: datetime
    review_status: Literal["pending"] = "pending"
    reviewer: None = None
    decided_at: None = None
    rationale: None = None


def sanctions_screening(findings: Sequence[Finding]) -> str:
    if any(f.kind == "sanctions_match" for f in findings):
        return POTENTIAL_MATCH
    if any(
        f.kind == "assessment" and f.scope == "sanctions" and f.value == "completed"
        for f in findings
    ):
        return NO_MATCH
    return NOT_RUN


def risk_indicators(findings: Sequence[Finding]) -> list[str]:
    kinds = {f.kind for f in findings}
    indicators = []
    if "pep_match" in kinds:
        indicators.append("pep")
    sanctions = sanctions_screening(findings)
    if sanctions == POTENTIAL_MATCH:
        indicators.append("sanctions")
    elif sanctions == NOT_RUN:
        indicators.append("sanctions_not_screened")
    if "adverse_media_match" in kinds:
        indicators.append("adverse_media")
    if "corporate_flag" in kinds:
        indicators.append("high_risk_jurisdiction")
    if "structuring" in kinds:
        indicators.append("structuring")
    return indicators


def evaluate_decision(findings: Sequence[Finding]) -> DecisionRecord:
    scores = risk_scorer(findings)
    indicators = risk_indicators(findings)
    sanctions = sanctions_screening(findings)
    tier, basis = score_tier(scores["overall"]), "score"
    if sanctions == POTENTIAL_MATCH:
        tier, basis = "CRITICAL", "sanctions_match"
    edd = "pep" in indicators
    gaps = gap_analyzer(indicators, {}, scores)
    return DecisionRecord(
        finding_ids=tuple(f.id for f in findings),
        risk_summary={
            "overall_risk_tier": tier,
            "overall_risk_score": scores["overall"],
            "tier_basis": basis,
            "sanctions_screening": sanctions,
            "edd_required": edd,
            "decision_recommendation": recommendation(tier, sanctions, edd),
        },
        dimension_scores=scores["dimensions"],
        obligations=tuple(gaps),
        recommended_actions=tuple(build_actions(tier, indicators, gaps)),
        evaluated_at=datetime.now(UTC),
    )


def recommendation(tier: str, sanctions: str = NO_MATCH, edd_required: bool = False) -> str:
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


def build_actions(tier: str, risk_indicators: list, gaps: list) -> list:
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
