import httpx
import pytest

from argus.ui import gradio_app
from argus.ui.gradio_app import format_report


def test_format_report_includes_executive_summary_and_ocr_visibility():
    report = {
        "report_id": "argus-rpt-demo-001",
        "entity": {"name": "Wirecard AG", "type": "corporate", "jurisdiction": "DE"},
        "risk_summary": {
            "overall_risk_tier": "HIGH",
            "overall_risk_score": 82,
            "confidence": 0.91,
            "decision_recommendation": "Enhanced Due Diligence",
        },
        "key_findings": ["Adverse Media", "Regulatory Triggers", "Ownership Risk"],
        "regulatory_triggers": [],
        "recommended_actions": [],
        "dimension_scores": {},
        "audit_trace": {},
        "timeline": [],
        "explanation": "Public enforcement history requires review.",
    }

    html = format_report(report)

    assert "ARGUS Decision" in html
    assert "Risk Tier: HIGH" in html
    assert "Risk Score" in html
    assert "Confidence" in html and "91%" in html
    assert "Enhanced Due Diligence" in html
    assert "Why This Risk Rating?" in html
    assert "Adverse Media" in html
    assert "OCR Visibility" in html
    assert "Upload" in html and "Extract" in html and "Investigate" in html


# ── report sections ───────────────────────────────────────────────────────────


def test_report_renders_dimensions_timeline_and_citations():
    report = {
        "risk_summary": {"overall_risk_tier": "HIGH", "confidence": 83},
        "dimension_scores": {"identity": {"score": 120, "tier": "CRITICAL"}},
        "timeline": [
            {"step": "Identity Agent", "time": "10:00:01"},
            {"step": "Screening Agent", "time": "10:00:02"},
            {"step": "Corporate Agent", "time": "10:00:03"},
            {"step": "Transaction Agent", "time": "10:00:04"},
            {"step": "Compliance & Risk Agent", "time": "10:00:05"},
        ],
        "audit_trace": {"identity_status": "completed", "screening_status": "error"},
        "regulatory_triggers": [
            {"rule": "FATF Rec.12", "foundry_iq_citation": {"document": "fatf<.pdf"}},
            {"rule": "No citation", "foundry_iq_citation": None},
        ],
        "recommended_actions": ["Escalate"],
    }

    page = format_report(report)

    assert "Risk Dimensions" in page
    assert 'height:8px;width:100%"' in page  # score 120 is clamped to a full bar
    assert "10:00:05" in page
    assert ">done<" in page and ">error<" in page
    assert "fatf&lt;.pdf" in page  # citation text is escaped
    assert "83%" in page  # confidence above 1 is already a percentage
    assert "<li>Escalate</li>" in page  # actions stand in for missing findings


def test_summary_without_findings_or_actions():
    page = gradio_app.format_executive_summary({})

    assert "No material drivers recorded" in page
    assert "UNKNOWN" in page


def test_branding_header():
    assert gradio_app._branding_header("") == ""
    assert "data:image/svg+xml" in gradio_app._branding_header("data:image/svg+xml;base64,AA")


def test_missing_logo_gives_empty_uri(monkeypatch):
    def unreadable(self):
        raise OSError("gone")

    monkeypatch.setattr(gradio_app.Path, "read_bytes", unreadable)

    assert gradio_app._logo_data_uri() == ""


# ── run_kyc_assessment: submit, poll, fetch ──────────────────────────────────


class FakeHttp:
    """Replaces the httpx module in the UI: scripted responses per URL suffix."""

    HTTPError = httpx.HTTPError

    def __init__(self, post=None, statuses=(), report=None):
        self._post = post
        self._statuses = list(statuses)
        self._report = report

    @staticmethod
    def _reply(url, body):
        if isinstance(body, Exception):
            raise body
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))

    def post(self, url, json, timeout):
        return self._reply(url, self._post)

    def get(self, url, timeout):
        if "/status/" in url:
            return self._reply(url, self._statuses.pop(0))
        return self._reply(url, self._report)


@pytest.fixture
def no_wait(monkeypatch):
    monkeypatch.setattr(gradio_app.time, "sleep", lambda seconds: None)


def _run(monkeypatch, fake):
    monkeypatch.setattr(gradio_app, "httpx", fake)
    return gradio_app.run_kyc_assessment("Acme", "corporate", "NL")


def test_blank_name_is_rejected():
    assert "Please enter an entity name" in gradio_app.run_kyc_assessment("  ", "corporate", "NL")


def test_submit_failure(monkeypatch, no_wait):
    page = _run(monkeypatch, FakeHttp(post=httpx.ConnectError("refused")))
    assert "API error: refused" in page


def test_completed_report_is_rendered(monkeypatch, no_wait):
    fake = FakeHttp(
        post={"report_id": "r1"},
        statuses=[{"status": "processing"}, {"status": "completed"}],
        report={"report_id": "r1", "risk_summary": {"overall_risk_tier": "LOW"}},
    )
    assert "Risk Tier: LOW" in _run(monkeypatch, fake)


def test_failed_assessment(monkeypatch, no_wait):
    fake = FakeHttp(post={"report_id": "r1"}, statuses=[{"status": "error"}])
    assert "Assessment failed" in _run(monkeypatch, fake)


def test_status_check_failure(monkeypatch, no_wait):
    fake = FakeHttp(post={"report_id": "r1"}, statuses=[httpx.ConnectError("lost")])
    assert "Status check failed: lost" in _run(monkeypatch, fake)


def test_timeout_after_sixty_polls(monkeypatch, no_wait):
    fake = FakeHttp(post={"report_id": "r1"}, statuses=[{"status": "processing"}] * 60)
    assert "timed out after 60 seconds" in _run(monkeypatch, fake)


def test_report_fetch_failure(monkeypatch, no_wait):
    fake = FakeHttp(
        post={"report_id": "r1"},
        statuses=[{"status": "completed"}],
        report=httpx.ConnectError("gone"),
    )
    assert "Report fetch failed: gone" in _run(monkeypatch, fake)
