"""pattern_detector — statistical AML pattern analysis on transaction history."""
from collections import Counter

STRUCTURING_THRESHOLD   = 10_000   # EUR — common reporting threshold
STRUCTURING_WINDOW_DAYS = 30
STRUCTURING_MIN_COUNT   = 5        # ≥5 transactions below threshold in window → flag

def pattern_detector(tx_history: dict) -> dict:
    transactions = tx_history.get("transactions", [])
    if not transactions:
        return {"structuring_flag": False, "layering_flag": False, "flagged_transactions": []}

    flagged = []
    # ── Structuring detection ─────────────────────────────────────────────────
    below_threshold = [t for t in transactions if t.get("amount", 0) < STRUCTURING_THRESHOLD]
    if len(below_threshold) >= STRUCTURING_MIN_COUNT:
        flagged.extend(below_threshold[:STRUCTURING_MIN_COUNT])

    # ── Layering detection (many unique counterparties in short window) ────────
    counterparties    = [t.get("counterparty") for t in transactions if t.get("counterparty")]
    unique_count      = len(set(counterparties))
    layering_flag     = unique_count > 20 and len(transactions) < 60

    structuring_flag  = len(below_threshold) >= STRUCTURING_MIN_COUNT
    return {
        "structuring_flag":     structuring_flag,
        "layering_flag":        layering_flag,
        "below_threshold_count":len(below_threshold),
        "unique_counterparties":unique_count,
        "flagged_transactions": flagged[:10],   # cap at 10 for report readability
    }
