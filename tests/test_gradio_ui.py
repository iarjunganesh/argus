from ui.gradio_app import format_report


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
