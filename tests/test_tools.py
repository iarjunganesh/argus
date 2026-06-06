"""tests/test_tools.py — Unit tests for ARGUS tools (all use mocks, no Azure needed)."""
import pytest
import asyncio

# ── Identity tools ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_identity_validator_name_match():
    from agents.identity.tools.identity_validator import identity_validator
    registry = {"found": True, "record": {"name": "Jane Doe", "date_of_birth": "1980-01-15"}}
    ocr = [{"fields": {"full_name": {"value": "Jane Doe"}, "date_of_birth": {"value": "1980-01-15"}}}]
    result = await identity_validator(registry, ocr)
    assert "name" in result["verified_fields"]
    assert result["confidence_score"] == 100

@pytest.mark.asyncio
async def test_identity_validator_name_mismatch():
    from agents.identity.tools.identity_validator import identity_validator
    registry = {"found": True, "record": {"name": "Jane Doe"}}
    ocr = [{"fields": {"full_name": {"value": "John Smith"}}}]
    result = await identity_validator(registry, ocr)
    assert len(result["discrepancies"]) == 1
    assert result["discrepancies"][0]["field"] == "name"
    assert result["confidence_score"] < 100

# ── Jurisdiction mapper ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jurisdiction_high_risk():
    from agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper
    result = await jurisdiction_mapper("KY")
    assert result["fatf_risk_tier"] == "high"
    assert len(result["special_measures"]) > 0

@pytest.mark.asyncio
async def test_jurisdiction_low_risk():
    from agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper
    result = await jurisdiction_mapper("SE")
    assert result["fatf_risk_tier"] == "low"

# ── Risk scorer ───────────────────────────────────────────────────────────────

def test_risk_scorer_high_risk():
    from agents.compliance.tools.risk_scorer import risk_scorer
    identity    = {"identity_score": 80}
    screening   = {"screening_risk_score": 90, "pep_hit": True, "adverse_media_hit": True, "sanctions_hit": False}
    corporate   = {"corporate_score": 40, "risk_flags": ["High-risk jurisdiction: KY"]}
    transaction = {"transaction_risk_score": 60, "structuring_flag": True}
    result = risk_scorer(identity, screening, corporate, transaction)
    assert result["overall"] > 50
    assert "screening" in result["dimensions"]

def test_risk_scorer_low_risk():
    from agents.compliance.tools.risk_scorer import risk_scorer
    result = risk_scorer(
        {"identity_score": 95},
        {"screening_risk_score": 0, "pep_hit": False, "adverse_media_hit": False, "sanctions_hit": False},
        {"corporate_score": 90, "risk_flags": []},
        {"transaction_risk_score": 0, "structuring_flag": False},
    )
    assert result["overall"] < 40

# ── Pattern detector ──────────────────────────────────────────────────────────

def test_pattern_detector_structuring():
    from agents.transaction.tools.pattern_detector import pattern_detector
    transactions = [{"amount": 9200, "counterparty": f"Co{i}"} for i in range(7)]
    result = pattern_detector({"transactions": transactions})
    assert result["structuring_flag"] is True
    assert result["below_threshold_count"] == 7

def test_pattern_detector_clean():
    from agents.transaction.tools.pattern_detector import pattern_detector
    transactions = [{"amount": 50000, "counterparty": "Big Corp"} for _ in range(5)]
    result = pattern_detector({"transactions": transactions})
    assert result["structuring_flag"] is False

# ── Gap analyzer ──────────────────────────────────────────────────────────────

def test_gap_analyzer_pep():
    from agents.compliance.tools.gap_analyzer import gap_analyzer
    gaps = gap_analyzer(["pep"], {}, {"overall": 60})
    assert any("PEP" in g or "pep" in g.lower() or "wealth" in g.lower() for g in gaps)

def test_gap_analyzer_clean():
    from agents.compliance.tools.gap_analyzer import gap_analyzer
    gaps = gap_analyzer([], {}, {"overall": 20})
    assert isinstance(gaps, list)
