"""
risk_scorer — Weighted risk scoring across all dimensions.
Weights: Screening 30% | Regulatory 25% | Identity 20% | Corporate 15% | Transaction 10%
"""

# Lower bound of each tier's score band, highest first.
TIER_BANDS = (("CRITICAL", 75), ("HIGH", 55), ("MEDIUM", 35), ("LOW", 0))

WEIGHTS = {
    "identity": 0.20,
    "screening": 0.30,
    "corporate": 0.15,
    "regulatory": 0.25,
    "transaction": 0.10,
}


def score_tier(score: float) -> str:
    """The tier whose score band holds `score`."""
    return next((name for name, floor in TIER_BANDS if score >= floor), "LOW")


def risk_scorer(identity: dict, screening: dict, corporate: dict, transaction: dict) -> dict:
    # Extract raw scores (0-100, where 100 = highest risk)
    identity_risk = 100 - identity.get("identity_score", 80)  # invert confidence
    screening_risk = screening.get("screening_risk_score", 0)
    corporate_risk = 100 - corporate.get("corporate_score", 80)
    transaction_risk = transaction.get("transaction_risk_score", 0)
    regulatory_risk = _estimate_regulatory_risk(screening, corporate)

    overall = (
        identity_risk * WEIGHTS["identity"]
        + screening_risk * WEIGHTS["screening"]
        + corporate_risk * WEIGHTS["corporate"]
        + regulatory_risk * WEIGHTS["regulatory"]
        + transaction_risk * WEIGHTS["transaction"]
    )

    # Heuristic boost for adverse-only public enforcement cases (e.g., Wirecard-style demos).
    # Keep this narrow so heavily signaled cases (sanctions/PEP) are not over-amplified into
    # CRITICAL solely because adverse media is also present.
    if (
        screening.get("adverse_media_hit")
        and screening.get("screening_risk_score", 0) >= 70
        and not screening.get("sanctions_hit")
        and not screening.get("pep_hit")
    ):
        overall += 12.0

    # Format weight strings from WEIGHTS constant for display
    def w(key):
        return f"{int(WEIGHTS[key] * 100)}%"

    return {
        "overall": round(overall, 1),
        "dimensions": {
            "identity": {
                "score": round(identity_risk, 1),
                "tier": score_tier(identity_risk),
                "weight": w("identity"),
            },
            "screening": {
                "score": round(screening_risk, 1),
                "tier": score_tier(screening_risk),
                "weight": w("screening"),
            },
            "corporate_ubo": {
                "score": round(corporate_risk, 1),
                "tier": score_tier(corporate_risk),
                "weight": w("corporate"),
            },
            "regulatory": {
                "score": round(regulatory_risk, 1),
                "tier": score_tier(regulatory_risk),
                "weight": w("regulatory"),
            },
            "transaction": {
                "score": round(transaction_risk, 1),
                "tier": score_tier(transaction_risk),
                "weight": w("transaction"),
            },
        },
    }


def _estimate_regulatory_risk(screening: dict, corporate: dict) -> float:
    score = 0.0
    # Make regulatory signals more sensitive for public adverse-media and PEP hits
    if screening.get("pep_hit"):
        score += 45
    if screening.get("adverse_media_hit"):
        score += 35
    if corporate.get("risk_flags"):
        score += len(corporate.get("risk_flags", [])) * 15
    return min(score, 100)
