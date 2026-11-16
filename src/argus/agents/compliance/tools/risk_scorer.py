"""The versioned risk policy: typed findings are its only case inputs.

An empty finding set has risks (20, 0, 20, 0, 0), score 7.0 and LOW tier. Missing assessments
are unknown, not cleared. Findings can affect several dimensions; contributions are not additive.
"""

from collections.abc import Sequence

from argus.findings import Category, Finding, collect_findings

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


def dimension_risks(findings: Sequence[Finding]) -> dict[str, int]:
    """Apply the live formulas, including category-level screening triggers and caps."""
    if len({f.id for f in findings}) != len(findings):
        raise ValueError("Duplicate finding identifiers")
    kinds = [f.kind for f in findings]
    assessed = {
        f.category
        for f in findings
        if f.kind != "assessment" or f.value in ("completed", "partial")
    }
    identity = sum(
        {"high": 30, "medium": 10}.get(str(f.value), 0) for f in findings if f.kind == "discrepancy"
    )
    flags = kinds.count("corporate_flag")
    return {
        "identity": min(identity, 100) if "identity" in assessed else 20,
        "screening": (
            60 * ("sanctions_match" in kinds)
            + 25 * ("pep_match" in kinds)
            + 15 * ("adverse_media_match" in kinds)
        ),
        "corporate": min(100, 15 * flags + 10 * ("ownership_depth" in kinds))
        if "corporate" in assessed
        else 20,
        "regulatory": min(
            100, 45 * ("pep_match" in kinds) + 35 * ("adverse_media_match" in kinds) + 15 * flags
        ),
        "transaction": min(
            100,
            40 * ("structuring" in kinds)
            + 30 * ("layering" in kinds)
            + 10 * kinds.count("typology"),
        ),
    }


def risk_scorer(findings: Sequence[Finding]) -> dict:
    risks = dimension_risks(findings)
    return {
        "overall": round(sum(risks[k] * weight for k, weight in WEIGHTS.items()), 1),
        "dimensions": {
            "corporate_ubo" if key == "corporate" else key: {
                "score": score,
                "tier": score_tier(score),
                "weight": f"{int(WEIGHTS[key] * 100)}%",
            }
            for key, score in risks.items()
        },
    }


def agent_score(category: Category, result: dict) -> int:
    """Derive a compatibility score through the same typed facts as Compliance."""
    records = collect_findings({category: {"result": result}})
    risk = dimension_risks(records.findings)[category]
    return 100 - risk if category in ("identity", "corporate") else risk
