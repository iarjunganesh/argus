# ARGUS — Execution Guide: June 8 → 14
## From current state to submission

> Archived planning note: superseded by docs/ARGUS_PreSubmission_Steps.md.
> Some steps here were pre-freeze explorations and are retained only for audit trail.

---

## STATUS DIAGNOSIS

The batch reports reveal two broken agents:
```
screening_status:  error  ← causes empty risk_summary
compliance_status: error  ← crashes on None from screening
```
**Everything else is working.** Fix these two things first — 15 minutes.
Then build the Explainability Agent — the single highest-impact addition.

---

## STEP 0 — IMMEDIATE FIXES (do right now, ~15 min)

### Fix A — `config.py` — fast-fail when Azure not configured

The current code calls `DefaultAzureCredential()` even when Azure is not
provisioned. It silently tries 6 credential sources (each 10–30s timeout),
causing agent requests to time out before the mock fallback ever fires.

**Open `config.py`. Replace the three client functions with these:**

```python
def get_cosmos_client():
    if not os.getenv("COSMOS_ENDPOINT"):
        raise RuntimeError("COSMOS_ENDPOINT not set — mock fallback will handle")
    from azure.cosmos import CosmosClient
    from azure.identity import DefaultAzureCredential
    return CosmosClient(url=os.environ["COSMOS_ENDPOINT"],
                        credential=DefaultAzureCredential())

def get_cosmos_database():
    return get_cosmos_client().get_database_client(
        os.environ.get("COSMOS_DATABASE", "argus-db"))

def get_foundry_client():
    if not os.getenv("FOUNDRY_ENDPOINT"):
        raise RuntimeError("FOUNDRY_ENDPOINT not set — mock fallback will handle")
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
        return AIProjectClient(endpoint=os.environ["FOUNDRY_ENDPOINT"],
                               credential=DefaultAzureCredential())
    except ImportError:
        raise RuntimeError("azure-ai-projects not installed — mock fallback will handle")
```

### Fix B — `agents/compliance/agent.py` — handle None upstream results

Find lines 29–32 (the four `upstream.get` lines). Replace with:

```python
# BEFORE (line ~29):
identity    = upstream.get("identity",    {}).get("result", {})
screening   = upstream.get("screening",   {}).get("result", {})
corporate   = upstream.get("corporate",   {}).get("result", {})
transaction = upstream.get("transaction", {}).get("result", {})

# AFTER — replace with:
identity    = upstream.get("identity",    {}).get("result") or {}
screening   = upstream.get("screening",   {}).get("result") or {}
corporate   = upstream.get("corporate",   {}).get("result") or {}
transaction = upstream.get("transaction", {}).get("result") or {}
```

The `or {}` converts `None` to `{}` when an upstream agent fails.
Previously `None.get("pep_hit")` crashed the compliance agent.

### Verify fixes worked

```bash
# Restart all agents and API, then run batch:
python scripts/batch_run_kyc.py --count 3 --out data/test_fix.jsonl

# Check the output — should now have content:
python -c "
import json
with open('data/test_fix.jsonl') as f:
    for line in f:
        r = json.loads(line)
        print(r['entity']['name'], '|', r['risk_summary'].get('overall_risk_tier','EMPTY'))
"
```

Expected output: `BatchCo-001 | LOW` (not `EMPTY`)

### Commit

```bash
git add config.py agents/compliance/agent.py
git commit -m "fix: fast-fail Azure clients, fix None upstream results in compliance agent"
git push
```

---

## STEP 1 — EXPLAINABILITY AGENT (June 8 PM, ~2 hours)

This is the single highest-impact addition. It makes the WHY of every risk
decision visible in plain English — judges understand ARGUS within 60 seconds.

### 1.1 Create `agents/compliance/tools/explain_decision.py`

```python
"""
explain_decision — LLM-powered plain English risk explanation.
Uses GitHub Models (free) or Azure OpenAI depending on config.
"""
from config import get_llm_client, MODEL_NAME


async def explain_decision(
    entity: dict,
    risk_summary: dict,
    dimension_scores: dict,
    key_findings: list,
    regulatory_triggers: list,
) -> str:
    """
    Generate a 3-5 sentence plain English explanation of the risk decision.
    Written as a compliance analyst would write it — specific, cited, actionable.
    """
    tier  = risk_summary.get("overall_risk_tier", "UNKNOWN")
    score = risk_summary.get("overall_risk_score", 0)

    findings_text = "\n".join(f"- {f}" for f in key_findings[:5])
    regs_text = "\n".join(
        f"- {r.get('rule', '')[:100]}" for r in regulatory_triggers[:3]
    )

    dim = dimension_scores
    dim_text = "\n".join([
        f"- Identity: {dim.get('identity',{}).get('score',0)}/100",
        f"- Screening: {dim.get('screening',{}).get('score',0)}/100",
        f"- Corporate/UBO: {dim.get('corporate_ubo',{}).get('score',0)}/100",
        f"- Transaction: {dim.get('transaction',{}).get('score',0)}/100",
        f"- Regulatory: {dim.get('regulatory',{}).get('score',0)}/100",
    ])

    prompt = f"""You are a senior KYC compliance analyst writing a risk assessment note.

Entity: {entity.get('name')} ({entity.get('type')}, jurisdiction: {entity.get('jurisdiction')})
Risk Score: {score}/100
Risk Tier: {tier}

Key findings identified:
{findings_text}

Regulatory rules triggered:
{regs_text}

Dimension risk scores (0=low risk, 100=high risk):
{dim_text}

Write exactly 3 to 5 sentences explaining WHY this entity received a {tier} risk rating.
Rules:
- Use plain English. Assume the reader is a bank manager, not a lawyer.
- Reference specific findings (e.g. "seven transactions below the reporting threshold").
- Reference specific regulations by name (e.g. "FATF Recommendation 12").
- Do NOT use bullet points or numbered lists — write flowing sentences only.
- Do NOT start with "The entity" — start with the most important risk factor directly.
- Be direct and professional."""

    try:
        client = get_llm_client()
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return _fallback_explanation(tier, key_findings)


def _fallback_explanation(tier: str, findings: list) -> str:
    """Used when LLM is unavailable."""
    if not findings:
        return f"This entity was assessed as {tier} risk based on the screening and compliance analysis."
    top = findings[0] if findings else "multiple risk indicators"
    return (
        f"This entity was assessed as {tier} risk. "
        f"The primary factor was: {top}. "
        f"A full review of all findings is recommended before making an onboarding decision."
    )
```

### 1.2 Wire into `agents/compliance/agent.py`

**Add import** at the top (after the existing imports):
```python
from agents.compliance.tools.explain_decision import explain_decision
```

**Add explanation call** inside `invoke()`, just before the final `return` statement:

```python
    # ── Explainability: plain English explanation of risk decision ────────────
    entity_info = {
        "name":         p.get("entity_name", "Unknown"),
        "type":         entity_type,
        "jurisdiction": jurisdiction,
    }
    explanation = await explain_decision(
        entity=entity_info,
        risk_summary={
            "overall_risk_tier":  tier,
            "overall_risk_score": overall_score,
        },
        dimension_scores=scores["dimensions"],
        key_findings=key_findings,
        regulatory_triggers=regulatory_triggers,
    )

    return {
        "agent":   "compliance",
        "task_id": message.task_id,
        "status":  "completed",
        "result": {
            "explanation": explanation,          # ← NEW
            "risk_summary": { ... },            # existing
            ...
        },
    }
```

**Full updated return block** (replace the entire existing `return` in `invoke()`):

```python
    explanation = await explain_decision(
        entity={"name": p.get("entity_name","Unknown"),
                "type": entity_type, "jurisdiction": jurisdiction},
        risk_summary={"overall_risk_tier": tier, "overall_risk_score": overall_score},
        dimension_scores=scores["dimensions"],
        key_findings=key_findings,
        regulatory_triggers=regulatory_triggers,
    )

    return {
        "agent":   "compliance",
        "task_id": message.task_id,
        "status":  "completed",
        "result": {
            "explanation":         explanation,
            "risk_summary": {
                "overall_risk_tier":       tier,
                "overall_risk_score":      overall_score,
                "confidence":              round(scores.get("confidence", 0.8), 2),
                "decision_recommendation": _recommendation(tier),
            },
            "dimension_scores":    scores["dimensions"],
            "key_findings":        key_findings,
            "regulatory_triggers": regulatory_triggers,
            "recommended_actions": recommended_actions,
            "compliance_gaps":     gaps,
            "foundry_iq_queries":  1,
        },
    }
```

### 1.3 Wire explanation into Orchestrator

In `agents/orchestrator/agent.py`, inside `synthesise_report()`, add:

```python
    # Pull explanation from compliance result
    explanation = comp_result.get("explanation", "")

    report = {
        "report_id":    f"argus-rpt-{task_id}",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "explanation":  explanation,           # ← ADD THIS LINE
        "entity": { ... },
        ...
    }
```

### 1.4 Show explanation in Gradio UI

In `ui/gradio_app.py`, inside `format_report()`, add this block
**immediately after the risk tier banner div** (after the closing `</div>`):

```python
    explanation = report.get("explanation", "")
    explanation_html = ""
    if explanation:
        explanation_html = f"""
      <div style="background:#f0f4ff;border-left:4px solid #3b5bdb;
                  padding:14px 16px;border-radius:6px;margin:12px 0;">
        <strong style="color:#3b5bdb;">🧠 Why this risk rating?</strong>
        <p style="margin:8px 0 0;line-height:1.6;color:#222;">{html.escape(explanation)}</p>
      </div>"""
```

Then add `{explanation_html}` to the returned HTML string, right after the tier banner.

### 1.5 Verify + commit

```bash
# Quick test — submit one request via API, check explanation appears
curl -s -X POST http://localhost:8000/api/v1/kyc/assess \
  -H "Content-Type: application/json" \
  -d '{"entity_name":"Test Corp","entity_type":"corporate","jurisdiction":"KY"}' | python -m json.tool

# Wait 5s, then check report
# (use report_id from above)

git add agents/compliance/tools/explain_decision.py \
        agents/compliance/agent.py \
        agents/orchestrator/agent.py \
        ui/gradio_app.py
git commit -m "feat: explainability agent — plain English risk explanation in report and UI"
git push
```

---

## STEP 2 — GRADIO UX REFRESH (June 11, ~2 hours)

### 2.1 Add agent activity section to `ui/gradio_app.py`

Add this helper function before `format_report()`:

```python
def format_agent_activity(report: dict) -> str:
    trace = report.get("audit_trace", {})
    agents = [
        ("🪪", "Identity",     trace.get("identity_status",    "—")),
        ("🔍", "Screening",    trace.get("screening_status",   "—")),
        ("🏢", "Corporate",    trace.get("corporate_status",   "—")),
        ("💳", "Transaction",  trace.get("transaction_status", "—")),
        ("⚖️", "Compliance",   trace.get("compliance_status",  "—")),
    ]
    rows = ""
    for icon, name, status in agents:
        color  = "#2ecc71" if status == "completed" else "#e74c3c" if status == "error" else "#888"
        label  = "✓ done" if status == "completed" else "✗ error" if status == "error" else status
        rows += f"""
        <div style="display:flex;align-items:center;gap:10px;
                    padding:8px 0;border-bottom:1px solid #eee;">
          <span style="font-size:1.2em">{icon}</span>
          <span style="flex:1;font-weight:500">{name} Agent</span>
          <span style="color:{color};font-size:0.85em;font-weight:600">{label}</span>
        </div>"""
    return f"""
    <div style="margin:16px 0;">
      <h3 style="margin-bottom:8px">Agent Activity (A2A)</h3>
      <div style="border:1px solid #eee;border-radius:8px;padding:8px 16px;">
        {rows}
      </div>
    </div>"""
```

### 2.2 Add dimension scores table

Add this helper:

```python
def format_dimension_scores(report: dict) -> str:
    dims = report.get("dimension_scores", {})
    if not dims:
        return ""
    rows = ""
    for key, label in [
        ("identity",     "Identity"),
        ("screening",    "Screening"),
        ("corporate_ubo","Corporate/UBO"),
        ("regulatory",   "Regulatory"),
        ("transaction",  "Transaction"),
    ]:
        d = dims.get(key, {})
        score = d.get("score", 0)
        tier  = d.get("tier", "—")
        tier_colors = {"LOW":"#2ecc71","MEDIUM":"#f39c12","HIGH":"#e74c3c","CRITICAL":"#8e1a0e"}
        color = tier_colors.get(tier, "#888")
        bar   = int(score)
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
            <span style="background:{color};color:white;padding:2px 8px;
                         border-radius:12px;font-size:0.75em">{tier}</span>
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
```

### 2.3 Update `format_report()` to use new helpers

Replace the current `return f"""..."""` in `format_report()` with:

```python
    agent_activity  = format_agent_activity(report)
    dimension_table = format_dimension_scores(report)

    return f"""
    <div style="font-family: sans-serif; max-width: 860px; color: #111;">
      <h2 style="margin-bottom:4px">ARGUS Risk Report</h2>
      <p style="color:#666;margin-top:0">
        <strong>ID:</strong> {report.get('report_id','')} &nbsp;|&nbsp;
        <strong>Entity:</strong> {report.get('entity',{}).get('name','')}
        ({report.get('entity',{}).get('type','')}) —
        {report.get('entity',{}).get('jurisdiction','')}
      </p>

      <div style="background:{color};color:white;padding:16px;border-radius:8px;margin:16px 0;">
        <h3 style="margin:0">Risk Tier: {tier} &nbsp;|&nbsp; Score: {score}/100</h3>
        <p style="margin:4px 0">{risk_summary.get('decision_recommendation','')}</p>
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

      <details>
        <summary style="cursor:pointer;color:#555;font-size:0.9em">
          📄 Full JSON Report
        </summary>
        <pre style="background:#f4f4f4;color:#111;padding:12px;font-size:12px;
                    line-height:1.4;white-space:pre-wrap;overflow:auto;
                    max-height:480px;border-radius:6px;">{pretty_json}</pre>
      </details>
    </div>"""
```

```bash
git add ui/gradio_app.py
git commit -m "feat: Gradio UX — agent activity timeline, dimension score bars, explanation panel"
git push
```

---

## STEP 3 — FOUNDRY IQ WIRING (June 12, once Azure Free Account ready)

This step is only possible once you have an Azure account.
**Skip this step if Azure account is not ready — mock fallbacks will run.**

### 3.1 One-click deploy

```bash
# Clone IQ Series repo and deploy to Azure
git clone https://github.com/microsoft/iq-series.git
cd iq-series
# Click "Deploy to Azure" button in the README
# OR use Azure CLI:
az group create --name argus-rg --location swedencentral
az deployment group create \
  --resource-group argus-rg \
  --template-file infra/main.bicep \
  --parameters resourcePrefix=argus
```

### 3.2 Copy values to `.env`

After deploy completes, go to Azure Portal → Resource Group `argus-rg` → Deployments → Outputs. Copy:

```bash
# Add to your .env file:
FOUNDRY_ENDPOINT=https://<your-project>.api.azureml.ms
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
AZURE_SEARCH_API_KEY=<your-key>
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### 3.3 Run IQ Series cookbooks (earn badge + learn the API)

```bash
cd iq-series
# Open each notebook in order:
# 1-Foundry-IQ-Unlocking-Knowledge-for-Agents/cookbook/
# 2-Foundry-IQ-Building-the-Data-Pipeline-with-Knowledge-Sources/cookbook/
# 3-Foundry-IQ-Querying-the-Multi-Source-AI-Knowledge-Bases/cookbook/
```

### 3.4 Create knowledge bases and index data

```bash
cd argus
python foundry_iq/create_knowledge_bases.py
python data/synthetic/generate_sanctions.py
python data/synthetic/generate_adverse_media.py
python foundry_iq/index_sanctions_and_media.py

# Download FATF 40 Recommendations PDF (public domain):
# https://www.fatf-gafi.org/content/dam/fatf-gafi/recommendations/FATF%20Recommendations%202012.pdf
# Save to: data/public/fatf_recommendations.pdf
python foundry_iq/index_regulations.py
```

### 3.5 Verify Foundry IQ is live

```bash
python -c "
from config import get_foundry_client, FOUNDRY_IQ_KB_REGULATIONS
client = get_foundry_client()
results = client.knowledge_bases.query(
    knowledge_base_name=FOUNDRY_IQ_KB_REGULATIONS,
    query='PEP enhanced due diligence requirements',
    top=2,
    include_citations=True
)
for r in results.items:
    print(r.content[:100], '|', r.relevance_score)
"
```

```bash
git add .env.example
git commit -m "feat: Foundry IQ knowledge bases wired — regulations, sanctions, adverse media"
git push
```

---

## STEP 4 — RECORDING SESSION (June 13)

### Pre-recording checklist

```
□ All 6 agents running (ports 8000–8005)
□ Gradio UI running (port 7860)
□ Test submission works end-to-end
□ ElevenLabs MP3 downloaded (trimmed script, ~4:30)
□ OBS installed and configured (1920×1080, no mic)
□ Browser zoom at 125%
□ Notifications off
```

### Agent startup commands (run each in a separate terminal)

```bash
# Terminal 1 — API Gateway
python -m uvicorn api.main:app --port 8000

# Terminal 2 — Identity Agent
python -m uvicorn agents.identity.agent:app --port 8001

# Terminal 3 — Screening Agent
python -m uvicorn agents.screening.agent:app --port 8002

# Terminal 4 — Corporate Agent
python -m uvicorn agents.corporate.agent:app --port 8003

# Terminal 5 — Compliance Agent
python -m uvicorn agents.compliance.agent:app --port 8004

# Terminal 6 — Transaction Agent
python -m uvicorn agents.transaction.agent:app --port 8005

# Terminal 7 — UI
python ui/gradio_app.py
```

### Health check (run before recording)

```bash
python -c "
import httpx
for port, name in [(8001,'identity'),(8002,'screening'),(8003,'corporate'),
                   (8004,'compliance'),(8005,'transaction')]:
    try:
        r = httpx.get(f'http://127.0.0.1:{port}/health', timeout=2)
        print(f'{name}: {r.json()[\"status\"]}')
    except:
        print(f'{name}: UNREACHABLE — restart terminal {port-7999}')
"
```

### Entities to demo (in this order)

| # | Entity Name | Type | Jurisdiction | Expected |
|---|---|---|---|---|
| 1 | `Cayman Synth Capital` | corporate | KY | HIGH |
| 2 | `Jane Synthetic` | individual | DE | LOW |

Submit #1 for the main demo (HIGH risk is more interesting).
Submit #2 at the end to show contrast (shows LOW risk = clean report).

### Recording sequence (synced to voiceover)

```
[0:00]  OBS: Start Recording — wait 3 seconds
[0:00]  Screen: Show README architecture section on GitHub
[0:30]  Screen: Keep on README — agent table visible
[1:30]  Screen: Switch to localhost:7860 (Gradio UI)
[1:45]  Type: "Cayman Synth Capital" / corporate / KY — slowly
[2:00]  Click: Submit — move mouse away
[2:10]  Wait for report to appear — do not click anything
[2:30]  Scroll: Down to risk tier banner — pause 5 seconds
[2:35]  Scroll: To 🧠 Explanation panel — pause 10 seconds (this is the money shot)
[2:50]  Scroll: To Regulatory Triggers — pause on citation — 10 seconds
[3:30]  Scroll: To Risk Dimensions table — show score bars
[3:45]  Scroll: To Agent Activity section — show all agents completed
[4:00]  Scroll: To Recommended Actions
[4:20]  Scroll: To Full JSON Report — click to expand — show audit trace
[4:30]  Switch: To github.com/iarjunganesh/argus
[4:45]  Scroll: README slowly
[5:00]  OBS: Stop Recording
```

---

## STEP 5 — SUBMISSION (June 14)

### Final checklist

```
□ Run pytest tests/ — all pass
□ README video link updated (not TODO)
□ GitHub repo is PUBLIC
□ repo has Topics added (azure-ai-foundry, foundry-iq, kyc, etc.)
□ Architecture diagram is in architecture/ folder
□ Demo video is on YouTube (Unlisted)
□ Microsoft Learn username ready
```

### Update README with video link

```bash
# Edit README.md:
# Change: 📹 [Demo Video](https://youtube.com/TODO)
# To:     📹 [Demo Video](https://youtu.be/YOUR_VIDEO_ID)

git add README.md
git commit -m "docs: add demo video link — submission ready"
git push
```

### Submit on Innovation Studio

1. Go to the hackathon portal
2. Click **Projects** → **New Project**
3. Fill in:
   - **Name:** ARGUS — Agentic Risk & Governance Unified Screening
   - **Track:** Reasoning Agents
   - **IQ Layer:** Foundry IQ
   - **GitHub URL:** https://github.com/iarjunganesh/argus
   - **Demo Video:** https://youtu.be/YOUR_VIDEO_ID
   - **Description:** (below)

**Project description to paste:**

```
ARGUS is a multi-agent KYC risk assessment system built on Azure AI Foundry.
A single compliance request is decomposed into 4 specialist agents running
in parallel via the A2A protocol: Identity, Screening, Corporate Intelligence,
and Transaction Intelligence. Their results are then passed to Compliance & Risk
as the fan-in step.

The intelligence layer is powered by Foundry IQ — with 3 knowledge bases for
regulatory text (FATF/4AMLD/6AMLD), sanctions data, and adverse media. Every
risk decision includes Foundry IQ citations traceable to specific regulatory
articles. An Explainability Agent generates a plain-English narrative explaining
WHY each entity received its risk rating.

All data is 100% synthetic. Built for the Reasoning Agents track.
```

### Deadline

**June 14, 2026 — 11:59 PM Pacific Time**

---

## QUICK REFERENCE — Git commit messages

```bash
# Step 0
git commit -m "fix: fast-fail Azure clients, fix None upstream in compliance agent"

# Step 1
git commit -m "feat: explainability agent — plain English risk narrative"

# Step 2
git commit -m "feat: Gradio UX — agent timeline, dimension bars, explanation panel"

# Step 3
git commit -m "feat: Foundry IQ knowledge bases wired"

# Final
git commit -m "docs: add demo video — submission ready"
```
