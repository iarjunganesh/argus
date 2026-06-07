"""
ARGUS Demo UI - Gradio
Submits KYC requests to the FastAPI backend and displays the risk report.
"""
import gradio as gr
import httpx
import time
import json
import os
import html

API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def format_agent_activity(report: dict) -> str:
    trace = report.get("audit_trace", {})
    timeline = report.get("timeline", [])
    latency = report.get("total_latency_seconds", "-")

    agents = [
        ("Identity Agent", trace.get("identity_status", "-")),
        ("Screening Agent", trace.get("screening_status", "-")),
        ("Corporate Agent", trace.get("corporate_status", "-")),
        ("Transaction Agent", trace.get("transaction_status", "-")),
        ("Compliance Agent", trace.get("compliance_status", "-")),
    ]

    ts = {}
    for entry in timeline:
        step = entry.get("step", "")
        step_time = entry.get("time", "")
        if "Identity" in step:
            ts["identity"] = step_time
        if "Screening" in step:
            ts["screening"] = step_time
        if "Corporate" in step:
            ts["corporate"] = step_time
        if "Transaction" in step:
            ts["transaction"] = step_time
        if "Compliance" in step:
            ts["compliance"] = step_time

    rows = ""
    for name, status in agents:
        color = "#2ecc71" if status == "completed" else "#e74c3c" if status == "error" else "#888"
        label = "done" if status == "completed" else "error" if status == "error" else status
        key = name.split()[0].lower()
        step_time = ts.get(key, "")
        rows += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #eee;">
            <span style="flex:1;font-weight:500">{name}</span>
            <span style="color:#999;font-size:0.8em;font-family:monospace">{step_time}</span>
            <span style="color:{color};font-size:0.82em;font-weight:600">{label}</span>
        </div>"""

    return f"""
    <div style="margin:16px 0;">
        <h3 style="margin-bottom:4px">Investigation Timeline</h3>
        <p style="color:#888;font-size:0.85em;margin-top:0">
            Total latency: <strong>{latency}s</strong>
        </p>
        <div style="border:1px solid #eee;border-radius:8px;padding:8px 16px;">
            {rows}
        </div>
    </div>"""


def format_dimension_scores(report: dict) -> str:
    dims = report.get("dimension_scores", {})
    if not dims:
        return ""

    rows = ""
    for key, label in [
        ("identity", "Identity"),
        ("screening", "Screening"),
        ("corporate_ubo", "Corporate/UBO"),
        ("regulatory", "Regulatory"),
        ("transaction", "Transaction"),
    ]:
        dimension = dims.get(key, {})
        score = dimension.get("score", 0)
        tier = dimension.get("tier", "-")
        tier_colors = {"LOW": "#2ecc71", "MEDIUM": "#f39c12", "HIGH": "#e74c3c", "CRITICAL": "#8e1a0e"}
        color = tier_colors.get(tier, "#888")
        bar = max(0, min(int(score), 100))
        rows += f"""
        <tr>
            <td style="padding:6px 12px;font-weight:500">{label}</td>
            <td style="padding:6px 12px">
                <div style="background:#eee;border-radius:4px;height:8px;width:100%">
                    <div style="background:{color};border-radius:4px;height:8px;width:{bar}%"></div>
                </div>
            </td>
            <td style="padding:6px 12px;text-align:center;color:{color};font-weight:600">{score}</td>
            <td style="padding:6px 12px;text-align:center">
                <span style="background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:0.75em">{tier}</span>
            </td>
        </tr>"""

    return f"""
    <div style="margin:16px 0;">
        <h3>Risk Dimensions</h3>
        <table style="width:100%;border-collapse:collapse;">
            <thead><tr style="background:#f8f9fa">
                <th style="padding:8px 12px;text-align:left">Dimension</th>
                <th style="padding:8px 12px;text-align:left">Score</th>
                <th style="padding:8px 12px;text-align:center">Value</th>
                <th style="padding:8px 12px;text-align:center">Tier</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""


def run_kyc_assessment(entity_name: str, entity_type: str, jurisdiction: str) -> str:
    if not entity_name.strip():
        return "<p style='color:red'>Please enter an entity name.</p>"

    try:
        resp = httpx.post(
            f"{API_BASE}/api/v1/kyc/assess",
            json={
                "entity_name": entity_name,
                "entity_type": entity_type,
                "jurisdiction": jurisdiction,
                "include_transaction_analysis": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        report_id = resp.json()["report_id"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        return f"<p style='color:red'>API error: {e}</p>"

    for _ in range(60):
        time.sleep(1)
        try:
            status_resp = httpx.get(f"{API_BASE}/api/v1/kyc/status/{report_id}", timeout=5)
            status_resp.raise_for_status()
            status = status_resp.json().get("status")
        except httpx.HTTPError as e:
            return f"<p style='color:red'>Status check failed: {e}</p>"
        if status == "completed":
            break
        if status == "error":
            return "<p style='color:red'>Assessment failed. Check API logs.</p>"
    else:
        return "<p style='color:red'>Assessment timed out after 60 seconds.</p>"

    try:
        report_resp = httpx.get(f"{API_BASE}/api/v1/kyc/report/{report_id}", timeout=10)
        report_resp.raise_for_status()
        report = report_resp.json()
    except httpx.HTTPError as e:
        return f"<p style='color:red'>Report fetch failed: {e}</p>"

    return format_report(report)


def format_report(report: dict) -> str:
    risk_summary = report.get("risk_summary", {})
    tier = risk_summary.get("overall_risk_tier", "UNKNOWN")
    score = risk_summary.get("overall_risk_score", 0)

    tier_colors = {"LOW": "#2ecc71", "MEDIUM": "#f39c12", "HIGH": "#e74c3c", "CRITICAL": "#8e1a0e"}
    color = tier_colors.get(tier, "#888")
    confidence = risk_summary.get("confidence", 0)
    confidence_pct = f"{int(confidence * 100)}%" if confidence <= 1 else f"{int(confidence)}%"

    findings_html = "".join(f"<li>{finding}</li>" for finding in report.get("key_findings", []))
    actions_html = "".join(f"<li>{action}</li>" for action in report.get("recommended_actions", []))

    regs_html = ""
    for trigger in report.get("regulatory_triggers", []):
        citation = trigger.get("foundry_iq_citation") or {}
        kb = citation.get("knowledge_base", "-")
        doc = citation.get("document", "-")
        article = citation.get("article", "-")
        regs_html += f"""
        <li style="margin-bottom:10px;">
            <strong>{trigger.get('rule', '')}</strong>
            <div style="font-size:0.85em;color:#555;margin-top:4px;">
                Citation: {html.escape(str(kb))} | {html.escape(str(doc))} | {html.escape(str(article))}
            </div>
        </li>"""

    trace = report.get("audit_trace", {})
    audit_trace_text = html.escape(
        "\n".join([
            f"task_id: {trace.get('task_id', '-')}",
            f"agents_invoked: {len(trace.get('agents_invoked', []))}",
            f"tool_calls: {trace.get('tool_calls', '-')}",
            f"foundry_iq_queries: {trace.get('foundry_iq_queries', '-')}",
        ])
    )
    audit_trace_html = f"""
    <div style="margin:16px 0;">
        <h3 style="color:#111;">Audit Trace</h3>
        <pre style="background:#f4f4f4;color:#111;padding:12px;font-size:12px;line-height:1.6;white-space:pre-wrap;overflow:auto;border-radius:6px;border:1px solid #eee;">{audit_trace_text}</pre>
    </div>"""

    explanation = report.get("explanation", "")
    explanation_html = ""
    if explanation:
        explanation_html = f"""
    <div style="background:#f0f4ff;border-left:4px solid #3b5bdb;padding:14px 16px;border-radius:6px;margin:12px 0;">
        <strong style="color:#3b5bdb;">Why this risk rating?</strong>
        <p style="margin:8px 0 0;line-height:1.6;color:#222;">{html.escape(explanation)}</p>
    </div>"""

    raw_json = json.dumps(report or {}, indent=2, ensure_ascii=False, default=str)
    if not raw_json.strip():
        raw_json = "{}"
    pretty_json = html.escape(raw_json)

    agent_activity = format_agent_activity(report)
    dimension_table = format_dimension_scores(report)

    return f"""
    <div style="font-family: sans-serif; max-width: 860px; color:#111;">
        <h2 style="margin-bottom:4px">ARGUS Risk Report</h2>
        <p style="color:#666;margin-top:0">
            <strong>ID:</strong> {report.get('report_id', '')} &nbsp;|&nbsp;
            <strong>Entity:</strong> {report.get('entity', {}).get('name', '')} ({report.get('entity', {}).get('type', '')}) - {report.get('entity', {}).get('jurisdiction', '')}
        </p>

        <div style="background:{color};color:white;padding:16px;border-radius:8px;margin:16px 0;">
            <h3 style="margin:0">Risk Tier: {tier} &nbsp;|&nbsp; Score: {score}/100</h3>
            <p style="margin:4px 0">{risk_summary.get('decision_recommendation', '')}</p>
            <p style="margin:4px 0;font-size:0.85em;opacity:0.85;">
                Confidence: <strong>{confidence_pct}</strong>
            </p>
        </div>

        {explanation_html}

        {dimension_table}

        {agent_activity}

        <h3>Key Findings</h3>
        <ul>{findings_html}</ul>

        <h3>Regulatory Triggers (Foundry IQ cited)</h3>
        <ul>{regs_html}</ul>

        <h3>Recommended Actions</h3>
        <ul>{actions_html}</ul>

        {audit_trace_html}

        <details>
            <summary style="cursor:pointer;color:#555;font-size:0.9em">Full JSON Report</summary>
            <pre style="background:#f4f4f4;color:#111;padding:12px;font-size:12px;line-height:1.4;white-space:pre-wrap;overflow:auto;max-height:480px;border-radius:6px;">{pretty_json}</pre>
        </details>
    </div>
    """


demo = gr.Interface(
    fn=run_kyc_assessment,
    inputs=[
        gr.Textbox(label="Entity Name", placeholder="e.g. Synthetic Holding GmbH"),
        gr.Dropdown(["individual", "corporate"], label="Entity Type", value="corporate"),
        gr.Textbox(label="Jurisdiction", placeholder="e.g. NL, DE, GB, SE"),
    ],
    outputs=gr.HTML(label="ARGUS Risk Report"),
    title="ARGUS - Agentic KYC Risk Assessment",
    description="Powered by Azure AI Foundry · Foundry IQ · A2A · GPT-4o | All data is synthetic.",
    theme=gr.themes.Soft(),
    examples=[
        ["Synthetic Holdings B.V.", "corporate", "NL"],
        ["Jane Synthetic", "individual", "DE"],
        ["Cayman Synth Capital", "corporate", "KY"],
    ],
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
