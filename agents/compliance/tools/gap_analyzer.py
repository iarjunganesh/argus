"""gap_analyzer — maps risk indicators to regulatory gaps and remediation steps."""

REGULATION_GAP_MAP = {
    "pep": [
        "FATF Rec.12 — Enhanced due diligence for PEPs not yet evidenced",
        "Source of wealth documentation required but not obtained",
    ],
    "sanctions": [
        "FATF Rec.6 — Targeted financial sanctions screening mandatory",
        "Transaction freeze obligations may apply — legal review required",
    ],
    "adverse_media": [
        "Risk-based approach requires adverse media to be weighed in onboarding decision",
    ],
    "high_risk_jurisdiction": [
        "FATF Rec.19 — Enhanced measures for high-risk countries required",
        "Correspondent relationship or business relationship requires senior management approval",
    ],
    "structuring": [
        "FATF Rec.20 — Suspicious transaction report (STR) filing obligation may be triggered",
        "Transaction monitoring alert escalation required",
    ],
}

def gap_analyzer(risk_indicators: list, regulations: dict, scores: dict) -> list:
    gaps = []
    for indicator in risk_indicators:
        gaps.extend(REGULATION_GAP_MAP.get(indicator, []))

    # Add generic gaps based on risk tier
    overall = scores.get("overall", 0)
    if overall >= 55 and "Enhanced CDD documentation" not in gaps:
        gaps.append("Enhanced Customer Due Diligence documentation pack required")
    if overall >= 75:
        gaps.append("Legal hold — do not execute transactions pending compliance clearance")

    return list(dict.fromkeys(gaps))  # deduplicate, preserve order
