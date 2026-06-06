"""
ARGUS Demo UI — Gradio
Submits KYC requests to the FastAPI backend and displays the risk report.
"""
import gradio as gr
import httpx, time, json, os

API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def run_kyc_assessment(entity_name: str, entity_type: str, jurisdiction: str) -> str:
    if not entity_name.strip():
        return "<p style='color:red'>Please enter an entity name.</p>"

    # Submit request
    try:
        resp = httpx.post(
            f"{API_BASE}/api/v1/kyc/assess",
            json={
                "entity_name":  entity_name,
                "entity_type":  entity_type,
                "jurisdiction": jurisdiction,
                "include_transaction_analysis": True,
            },
            timeout=10,
        )
        report_id = resp.json()["report_id"]
    except Exception as e:
        return f"<p style='color:red'>API error: {e}</p>"

    # Poll for completion (max 60s)
    for _ in range(60):
        time.sleep(1)
        status_resp = httpx.get(f"{API_BASE}/api/v1/kyc/status/{report_id}", timeout=5)
        status = status_resp.json().get("status")
        if status == "completed":
            break
        if status == "error":
            return "<p style='color:red'>Assessment failed. Check API logs.</p>"

    # Fetch report
    report_resp = httpx.get(f"{API_BASE}/api/v1/kyc/report/{report_id}", timeout=10)
    report = report_resp.json()

    return format_report(report)


def format_report(report: dict) -> str:
    risk_summary = report.get("risk_summary", {})
    tier  = risk_summary.get("overall_risk_tier", "UNKNOWN")
    score = risk_summary.get("overall_risk_score", 0)

    tier_colors = {"LOW": "#2ecc71", "MEDIUM": "#f39c12", "HIGH": "#e74c3c", "CRITICAL": "#8e1a0e"}
    color = tier_colors.get(tier, "#888")

    findings_html = "".join(
        f"<li>{f}</li>" for f in report.get("key_findings", [])
    )
    actions_html = "".join(
        f"<li>{a}</li>" for a in report.get("recommended_actions", [])
    )
    regs_html = "".join(
        f"<li><strong>{r.get('rule','')}</strong></li>"
        for r in report.get("regulatory_triggers", [])
    )

    return f"""
    <div style="font-family: sans-serif; max-width: 800px;">
      <h2>ARGUS Risk Report</h2>
      <p><strong>Report ID:</strong> {report.get('report_id','')}</p>
      <p><strong>Entity:</strong> {report.get('entity',{}).get('name','')} ({report.get('entity',{}).get('type','')}) — {report.get('entity',{}).get('jurisdiction','')}</p>

      <div style="background:{color};color:white;padding:16px;border-radius:8px;margin:16px 0;">
        <h3 style="margin:0">Risk Tier: {tier} &nbsp;|&nbsp; Score: {score}/100</h3>
        <p style="margin:4px 0">{risk_summary.get('decision_recommendation','')}</p>
      </div>

      <h3>Key Findings</h3>
      <ul>{findings_html}</ul>

      <h3>Regulatory Triggers (Foundry IQ cited)</h3>
      <ul>{regs_html}</ul>

      <h3>Recommended Actions</h3>
      <ul>{actions_html}</ul>

      <details>
        <summary>Full JSON Report</summary>
        <pre style="background:#f4f4f4;padding:12px;font-size:12px;">{json.dumps(report, indent=2)}</pre>
      </details>
    </div>
    """


demo = gr.Interface(
    fn=run_kyc_assessment,
    inputs=[
        gr.Textbox(label="Entity Name",         placeholder="e.g. Synthetic Holding GmbH"),
        gr.Dropdown(["individual", "corporate"], label="Entity Type", value="corporate"),
        gr.Textbox(label="Jurisdiction",         placeholder="e.g. NL, DE, GB, SE"),
    ],
    outputs=gr.HTML(label="ARGUS Risk Report"),
    title="ARGUS — Agentic KYC Risk Assessment",
    description="Powered by Azure AI Foundry · Foundry IQ · A2A · GPT-4o | All data is synthetic.",
    theme=gr.themes.Soft(),
    examples=[
        ["Synthetic Holdings B.V.", "corporate", "NL"],
        ["Jane Synthetic",          "individual", "DE"],
        ["Cayman Synth Capital",    "corporate",  "KY"],
    ],
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
