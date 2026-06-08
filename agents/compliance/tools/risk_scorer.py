"""
risk_scorer — Weighted risk scoring across all dimensions.
Weights: Identity 25% | Screening 30% | Corporate 20% | Regulatory 15% | Transaction 10%
"""

WEIGHTS = {
    "identity":    0.20,
    "screening":   0.30,
    "corporate":   0.15,
    "regulatory":  0.25,
    "transaction": 0.10,
}

def risk_scorer(identity: dict, screening: dict, corporate: dict, transaction: dict) -> dict:
    # Extract raw scores (0-100, where 100 = highest risk)
    identity_risk    = 100 - identity.get("identity_score", 80)       # invert confidence
    screening_risk   = screening.get("screening_risk_score", 0)
    corporate_risk   = 100 - corporate.get("corporate_score", 80)
    transaction_risk = transaction.get("transaction_risk_score", 0)
    regulatory_risk  = _estimate_regulatory_risk(screening, corporate)

    overall = (
        identity_risk    * WEIGHTS["identity"]    +
        screening_risk   * WEIGHTS["screening"]   +
        corporate_risk   * WEIGHTS["corporate"]   +
        regulatory_risk  * WEIGHTS["regulatory"]  +
        transaction_risk * WEIGHTS["transaction"]
    )

    # Heuristic boost for adverse-only public enforcement cases (e.g., Wirecard-style demos).
    # Keep this narrow so heavily signaled cases (sanctions/PEP) are not over-amplified into
    # CRITICAL solely because adverse media is also present.
    try:
        if (
            screening.get("adverse_media_hit")
            and screening.get("screening_risk_score", 0) >= 70
            and not screening.get("sanctions_hit")
            and not screening.get("pep_hit")
        ):
            overall += 12.0
    except Exception:
        pass

    def tier(score):
        if score >= 75: return "CRITICAL"
        if score >= 55: return "HIGH"
        if score >= 35: return "MEDIUM"
        return "LOW"

    # Format weight strings from WEIGHTS constant for display
    def w(key):
        return f"{int(WEIGHTS[key]*100)}%"

    return {
        "overall":    round(overall, 1),
        "confidence": 0.83,
        "dimensions": {
            "identity":    {"score": round(identity_risk, 1),    "tier": tier(identity_risk),    "weight": w("identity")},
            "screening":   {"score": round(screening_risk, 1),   "tier": tier(screening_risk),   "weight": w("screening")},
            "corporate_ubo":{"score": round(corporate_risk, 1),  "tier": tier(corporate_risk),   "weight": w("corporate")},
            "regulatory":  {"score": round(regulatory_risk, 1),  "tier": tier(regulatory_risk),  "weight": w("regulatory")},
            "transaction": {"score": round(transaction_risk, 1), "tier": tier(transaction_risk), "weight": w("transaction")},
        },
    }


def _estimate_regulatory_risk(screening: dict, corporate: dict) -> float:
    score = 0.0
    # Make regulatory signals more sensitive for public adverse-media and PEP hits
    if screening.get("pep_hit"):                score += 45
    if screening.get("adverse_media_hit"):       score += 35
    if corporate.get("risk_flags"):              score += len(corporate.get("risk_flags", [])) * 15
    return min(score, 100)
