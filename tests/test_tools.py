"""tests/test_tools.py — Unit tests for ARGUS tools (all use mocks, no Azure needed)."""
import pytest
import asyncio
import sys
import types

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


@pytest.mark.asyncio
async def test_ocr_processor_azure_doc_intelligence_success(monkeypatch):
    from agents.identity.tools.ocr_processor import ocr_processor

    class FakeField:
        def __init__(self, value, confidence):
            self.value = value
            self.confidence = confidence

    class FakeDoc:
        def __init__(self):
            self.fields = {
                "full_name": FakeField("Jane Doe", 0.99),
                "passport_number": FakeField("P123", 0.98),
            }

    class FakeResult:
        def __init__(self):
            self.documents = [FakeDoc()]

    class FakePoller:
        def result(self):
            return FakeResult()

    class FakeDocumentAnalysisClient:
        def __init__(self, endpoint=None, credential=None):
            self.endpoint = endpoint
            self.credential = credential

        def begin_analyze_document(self, model_id, document=None):
            return FakePoller()

    class FakeAzureKeyCredential:
        def __init__(self, key):
            self.key = key

    # Inject minimal Azure SDK module tree expected by ocr_processor.
    azure_mod = types.ModuleType("azure")
    ai_mod = types.ModuleType("azure.ai")
    form_mod = types.ModuleType("azure.ai.formrecognizer")
    core_mod = types.ModuleType("azure.core")
    cred_mod = types.ModuleType("azure.core.credentials")
    form_mod.DocumentAnalysisClient = FakeDocumentAnalysisClient
    cred_mod.AzureKeyCredential = FakeAzureKeyCredential

    monkeypatch.setitem(sys.modules, "azure", azure_mod)
    monkeypatch.setitem(sys.modules, "azure.ai", ai_mod)
    monkeypatch.setitem(sys.modules, "azure.ai.formrecognizer", form_mod)
    monkeypatch.setitem(sys.modules, "azure.core", core_mod)
    monkeypatch.setitem(sys.modules, "azure.core.credentials", cred_mod)

    monkeypatch.setenv("DOC_INTELLIGENCE_ENDPOINT", "https://example.cognitiveservices.azure.com")
    monkeypatch.setenv("DOC_INTELLIGENCE_KEY", "fake-key")

    result = await ocr_processor("SGVsbG8=", "passport")
    assert result["source"] == "azure_doc_intelligence"
    assert result["fields"]["full_name"]["value"] == "Jane Doe"

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


@pytest.mark.asyncio
async def test_jurisdiction_medium_risk():
    from agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper
    result = await jurisdiction_mapper("ng")
    assert result["country_code"] == "NG"
    assert result["fatf_risk_tier"] == "medium"
    assert "monitoring" in result["special_measures"][0].lower()


@pytest.mark.asyncio
async def test_jurisdiction_unknown_when_missing_code():
    from agents.corporate.tools.jurisdiction_mapper import jurisdiction_mapper
    result = await jurisdiction_mapper("")
    assert result["country_code"] == ""
    assert result["fatf_risk_tier"] == "unknown"
    assert result["special_measures"] == []

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
