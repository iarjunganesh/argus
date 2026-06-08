# ARGUS — Pre-Submission Steps
### Feature freeze is in effect. No new agents, services, or infrastructure.

---

## STEP 1 — Confidence score in UI (15 min)

**File:** `ui/gradio_app.py`

Inside `format_report()`, find the risk tier banner block and replace it:

```python
# BEFORE:
    return f"""
    <div style="...">
      ...
      <div style="background:{color};color:white;padding:16px;border-radius:8px;margin:16px 0;">
        <h3 style="margin:0">Risk Tier: {tier} &nbsp;|&nbsp; Score: {score}/100</h3>
        <p style="margin:4px 0">{risk_summary.get('decision_recommendation','')}</p>
      </div>

# AFTER — add confidence line:
    confidence     = risk_summary.get("confidence", 0)
    confidence_pct = f"{int(confidence * 100)}%" if confidence <= 1 else f"{int(confidence)}%"

    return f"""
    <div style="...">
      ...
      <div style="background:{color};color:white;padding:16px;border-radius:8px;margin:16px 0;">
        <h3 style="margin:0">Risk Tier: {tier} &nbsp;|&nbsp; Score: {score}/100</h3>
        <p style="margin:4px 0">{risk_summary.get('decision_recommendation','')}</p>
        <p style="margin:4px 0;font-size:0.85em;opacity:0.85;">
          Confidence: <strong>{confidence_pct}</strong>
        </p>
      </div>
```

### Verify
Submit a KYC request in the browser. The red/orange/green banner should now show:
```
Risk Tier: HIGH | Score: 74/100
Enhanced Due Diligence required before onboarding.
Confidence: 83%
```

### Commit
```bash
git add ui/gradio_app.py
git commit -m "feat: show confidence score in risk tier banner"
git push
```

---

## STEP 2 — Investigation Timeline timestamps (20 min)

**File:** `agents/orchestrator/agent.py`

Inside `run_kyc_assessment()`, capture timestamps for each agent call.
Replace the parallel tasks section with:

```python
from datetime import datetime, timezone

async def run_kyc_assessment(kyc_request: dict) -> dict:
    import uuid
    task_id   = f"kyc-{uuid.uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)

    # ── Fan-out (parallel) ────────────────────────────────────────────
    t0 = datetime.now(timezone.utc)
    parallel_tasks = [
        call_agent("identity",    kyc_request, task_id),
        call_agent("screening",   kyc_request, task_id),
        call_agent("corporate",   kyc_request, task_id),
        call_agent("transaction", kyc_request, task_id),
    ]
    parallel_results = await asyncio.gather(*parallel_tasks)
    identity_result, screening_result, corporate_result, transaction_result = parallel_results
    t1 = datetime.now(timezone.utc)

    # ── Fan-in ────────────────────────────────────────────────────────
    compliance_payload = {
        **kyc_request,
        "upstream_results": {
            "identity":    identity_result,
            "screening":   screening_result,
            "corporate":   corporate_result,
            "transaction": transaction_result,
        },
    }
    compliance_result = await call_agent("compliance", compliance_payload, task_id)
    t2 = datetime.now(timezone.utc)

    report = await synthesise_report(
        task_id, kyc_request,
        identity_result, screening_result,
        corporate_result, transaction_result,
        compliance_result,
    )

    # ── Add timeline to report ────────────────────────────────────────
    report["timeline"] = [
        {"step": "Request received",         "time": started_at.strftime("%H:%M:%S")},
        {"step": "Identity Agent",           "time": t0.strftime("%H:%M:%S")},
        {"step": "Screening Agent",          "time": t0.strftime("%H:%M:%S")},
        {"step": "Corporate Agent",          "time": t0.strftime("%H:%M:%S")},
        {"step": "Transaction Agent",        "time": t0.strftime("%H:%M:%S")},
        {"step": "Parallel agents complete", "time": t1.strftime("%H:%M:%S")},
        {"step": "Compliance & Risk Agent",  "time": t1.strftime("%H:%M:%S")},
        {"step": "Final report generated",   "time": t2.strftime("%H:%M:%S")},
    ]
    report["total_latency_seconds"] = round((t2 - started_at).total_seconds(), 2)
    return report
```

**File:** `ui/gradio_app.py`

Replace the `format_agent_activity()` function with a timestamped version:

```python
def format_agent_activity(report: dict) -> str:
    trace    = report.get("audit_trace", {})
    timeline = report.get("timeline", [])
    latency  = report.get("total_latency_seconds", "—")

    agents = [
        ("🪪", "Identity Agent",    trace.get("identity_status",    "—")),
        ("🔍", "Screening Agent",   trace.get("screening_status",   "—")),
        ("🏢", "Corporate Agent",   trace.get("corporate_status",   "—")),
        ("💳", "Transaction Agent", trace.get("transaction_status", "—")),
        ("⚖️", "Compliance Agent",  trace.get("compliance_status",  "—")),
    ]

    # Build timestamp lookup from timeline
    ts = {}
    for entry in timeline:
        step = entry.get("step", "")
        time = entry.get("time", "")
        if "Identity"    in step: ts["identity"]    = time
        if "Screening"   in step: ts["screening"]   = time
        if "Corporate"   in step: ts["corporate"]   = time
        if "Transaction" in step: ts["transaction"] = time
        if "Compliance"  in step: ts["compliance"]  = time

    rows = ""
    for icon, name, status in agents:
        color = "#2ecc71" if status == "completed" else "#e74c3c" if status == "error" else "#888"
        label = "✓ done" if status == "completed" else "✗ error" if status == "error" else status
        key   = name.split()[0].lower()
        time  = ts.get(key, "")
        rows += f"""
        <div style="display:flex;align-items:center;gap:10px;
                    padding:8px 0;border-bottom:1px solid #eee;">
          <span style="font-size:1.1em">{icon}</span>
          <span style="flex:1;font-weight:500">{name}</span>
          <span style="color:#999;font-size:0.8em;font-family:monospace">{time}</span>
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
```

### Commit
```bash
git add agents/orchestrator/agent.py ui/gradio_app.py
git commit -m "feat: timestamped investigation timeline + total latency in UI"
git push
```

---

## STEP 3 — README polish (30 min)

**File:** `README.md`

Add these two sections immediately **before** the `## Architecture` heading:

```markdown
## The Problem

KYC compliance requires a human analyst to simultaneously verify identity,
screen sanctions lists, resolve corporate ownership structures, and assess
regulatory risk. Done manually, this takes 2–5 days per customer and costs
financial institutions billions in compliance overhead annually. A missed
risk can result in multi-million dollar regulatory fines.

## How ARGUS Works

1. Submit an entity name, type, and jurisdiction
2. ARGUS fires 5 specialist agents simultaneously via the A2A protocol
3. Foundry IQ retrieves cited, grounded answers from regulatory knowledge bases
4. Compliance agent synthesises a weighted risk score, plain-English explanation, and action plan
5. Every decision is fully traceable — agent by agent, tool by tool, citation by citation
```

Also update the `## Demo` section at the bottom to add the three scenarios:

```markdown
## Demo

📹 [Demo Video](https://youtube.com/TODO) *(updated on submission day)*

### Demo Scenarios

| Scenario | Entity | Type | Jurisdiction | Expected Outcome |
|---|---|---|---|---|
| 🔴 High Risk | `Cayman Synth Capital` | corporate | KY | HIGH — Enhanced Due Diligence |
| 🟠 Public Signal | `Wirecard AG` | corporate | DE | Screening-elevated with cited adverse media |
| 🟡 Medium Risk | `Synthetic Holdings B.V.` | corporate | NL | MEDIUM — Elevated monitoring |
```

### Commit
```bash
git add README.md
git commit -m "docs: add Problem, How It Works, and demo scenarios to README"
git push
```

---

## STEP 4 — Foundry IQ Knowledge Bases (45 min)

Index real regulatory data and synthetic datasets into the three Foundry IQ
knowledge bases. This makes citations appear in the risk report — visible
proof of IQ integration for judges.

### 4.1 — KB-Regulations: index real FATF PDF (public domain)

```bash
# Download FATF 40 Recommendations — public domain, free
curl -L "https://www.fatf-gafi.org/content/dam/fatf-gafi/recommendations/FATF%20Recommendations%202012.pdf" \
     -o data/public/fatf_recommendations.pdf

# Verify download (~500KB)
ls -lh data/public/fatf_recommendations.pdf
```

```bash
# Index into KB-Regulations
python foundry_iq/index_regulations.py
```

**Verify citations appear:**
```bash
python -c "
from config import get_foundry_client, FOUNDRY_IQ_KB_REGULATIONS
client = get_foundry_client()
results = client.knowledge_bases.query(
    knowledge_base_name=FOUNDRY_IQ_KB_REGULATIONS,
    query='PEP politically exposed person enhanced due diligence',
    top=2,
    include_citations=True
)
for r in results.items:
    print('TEXT:    ', r.content[:80])
    print('CITATION:', r.citation.document_title if r.citation else 'none')
    print('---')
"
```

Expected output:
```
TEXT:     Countries should apply enhanced due diligence measures to business
CITATION: fatf_recommendations.pdf
---
```

If citations appear → the risk report will show real FATF article references. ✅

---

### 4.2 — KB-Sanctions and KB-AdverseMedia: index synthetic data

Do NOT wire real OFAC/UN lists — too large, slow, and risky for demo.
Synthetic core data with realistic schema is sufficient for the hackathon.

```bash
# Generate if not already done
python data/synthetic/generate_sanctions.py
python data/synthetic/generate_adverse_media.py

# Index into Foundry IQ KBs
python foundry_iq/index_sanctions_and_media.py
```

**Verify sanctions KB:**
```bash
python -c "
from config import get_foundry_client, FOUNDRY_IQ_KB_SANCTIONS
client = get_foundry_client()
results = client.knowledge_bases.query(
    knowledge_base_name=FOUNDRY_IQ_KB_SANCTIONS,
    query='narcotics sanctions designation',
    top=2,
    include_citations=True
)
for r in results.items:
    print('HIT:', r.content[:80], '| score:', round(r.relevance_score, 2))
"
```

### 4.3 — Commit

```bash
git add data/public/fatf_recommendations.pdf \
        data/synthetic/sanctions.jsonl \
        data/synthetic/adverse_media.jsonl
git commit -m "data: index FATF PDF into KB-Regulations, synthetic data into KB-Sanctions and KB-AdverseMedia"
git push
```

> **Note:** KB-Regulations uses the real FATF public document — citations will
> reference specific article numbers and page numbers. KB-Sanctions uses synthetic
> data, while KB-AdverseMedia may combine synthetic and public-source summaries for
> realistic screening demonstrations.

---

## STEP 5 — OCR test (20 min, decide before recording)

Test OCR privately before committing to it in the demo recording.

### Create a synthetic test document image

```python
# Run this once to create a fake passport image for testing
# Save as scripts/create_test_doc.py

from PIL import Image, ImageDraw, ImageFont
import os

def create_synthetic_passport():
    img = Image.new("RGB", (600, 400), color="#1a3a6b")
    draw = ImageDraw.Draw(img)

    draw.rectangle([20, 20, 580, 380], outline="gold", width=3)
    draw.text((30, 40),  "SYNTHETIC PASSPORT",      fill="gold")
    draw.text((30, 100), "Surname:    SYNTHETIC",   fill="white")
    draw.text((30, 130), "Given Name: JANE",        fill="white")
    draw.text((30, 160), "Nationality: DEU",        fill="white")
    draw.text((30, 190), "DOB:         1985-03-22", fill="white")
    draw.text((30, 220), "Passport No: SYN8472910", fill="white")
    draw.text((30, 250), "Expiry:      2030-03-22", fill="white")
    draw.text((30, 310), "SYNTHETIC DOCUMENT — NOT REAL", fill="yellow")

    path = "data/synthetic/test_passport.png"
    img.save(path)
    print(f"Saved: {path}")

create_synthetic_passport()
```

```bash
pip install pillow --break-system-packages
python scripts/create_test_doc.py
```

### Test OCR endpoint

```bash
curl -s -X POST http://localhost:8000/api/v1/kyc/document/ocr \
  -F "file=@data/synthetic/test_passport.png" \
  -F "doc_type=passport" | python -m json.tool
```

### Decision

| Result | Action |
|---|---|
| Returns name, DOB, passport number | ✅ Include OCR in demo recording |
| Returns empty or mock fields only | ❌ Skip OCR in recording — mention in README as supported capability |

---

## STEP 6 — Demo recording

### Two primary scenarios to record (in this order)

**Scenario 1 — HIGH risk** *(main demo, most time spent here)*
- Entity: `Cayman Synth Capital`
- Type: `corporate`
- Jurisdiction: `KY`
- What to show: Explanation panel (blue), HIGH tier (red), Foundry IQ citations,
  Investigation Timeline with timestamps, structuring pattern in transaction findings

**Scenario 2 — Public-source adverse-media contrast** *(show contrast — 60 seconds)*
- Entity: `Wirecard AG`
- Type: `corporate`
- Jurisdiction: `DE`
- What to show: screening-driven risk, public-source citation metadata, contrast to Cayman typology case

**Scenario 3 — MEDIUM risk** *(optional, if time permits)*
- Entity: `Synthetic Holdings B.V.`
- Type: `corporate`
- Jurisdiction: `NL`

### Recording sequence

### Voiceover sync map

| Voiceover beat | Screen action |
|---|---|
| 0:00–0:30 Problem | Show architecture diagram |
| 0:30–1:30 What is ARGUS | Stay on architecture and scroll to the agent table |
| 1:30–2:35 Live demo case 1 | Switch to Gradio and submit Cayman Synth Capital |
| 2:35–3:20 Foundry IQ on case 1 | Scroll to Regulatory Triggers and citations |
| 3:20–4:20 Live demo case 2 | Submit Wirecard AG and show contrast |
| 4:20–4:55 Closing | Switch to GitHub repo and end on the README |

```
[0:00]  OBS: Start Recording — wait 3 seconds
[0:00]  Screen: Tab 3 — architecture/ARGUS_Architecture.md on GitHub
[0:30]  Screen: Stay on architecture — scroll to agent table
[1:30]  Screen: Switch to Tab 1 — localhost:7860 (Gradio UI)
[1:40]  Type: Cayman Synth Capital / corporate / KY — type slowly
[2:00]  Click: Submit — move mouse away
[2:10]  Wait: Report loads — if needed, briefly hold on the sequence diagram fan-out/fan-in view while the audio covers the gap
[2:30]  Scroll: Risk tier banner — pause (show HIGH + confidence %)
[2:40]  Scroll: Explanation panel — pause 10 seconds (money shot)
[3:00]  Scroll: Regulatory Triggers — pause on citation
[3:20]  Scroll: Investigation Timeline — pause to show timestamps
[3:40]  Scroll: Recommended Actions
[3:55]  Clear form — type: Wirecard AG / corporate / DE
[4:05]  Click: Submit
[4:25]  Report loads — pause on screening-driven decision and citations (contrast)
[4:35]  Switch: Tab 2 — github.com/iarjunganesh/argus
[4:45]  Scroll: README slowly
[5:00]  OBS: Stop Recording
```

### Startup commands (before recording)

```bash
# 7 separate terminals
python -m uvicorn api.main:app --port 8000
python -m uvicorn agents.identity.agent:app --port 8001
python -m uvicorn agents.screening.agent:app --port 8002
python -m uvicorn agents.corporate.agent:app --port 8003
python -m uvicorn agents.transaction.agent:app --port 8004
python -m uvicorn agents.compliance.agent:app --port 8005
python ui/gradio_app.py
```

### Health check before hitting record

```bash
python -c "
import httpx
for port, name in [(8001,'identity'),(8002,'screening'),(8003,'corporate'),
                   (8004,'transaction'),(8005,'compliance')]:
    try:
        r = httpx.get(f'http://127.0.0.1:{port}/health', timeout=2)
        print(f'{name}: {r.json()[\"status\"]}')
    except Exception as e:
        print(f'{name}: UNREACHABLE')
"
```

---

## STEP 7 — Combine audio + video

1. Open **Clipchamp** (Windows) or **iMovie** (Mac)
2. Import OBS recording → drag to timeline
3. Import `argus_voiceover.mp3` → drag below video track
4. Right-click video track → **Mute**
5. Check sync — nudge MP3 left/right if needed
6. Export → **1080p MP4**

---

## STEP 8 — Upload + update README

```bash
# After YouTube upload (Unlisted):
# Edit README.md — find:
# 📹 [Demo Video](https://youtube.com/TODO)
# Replace with:
# 📹 [Demo Video](https://youtu.be/YOUR_VIDEO_ID)

git add README.md
git commit -m "docs: add demo video link — submission ready"
git push
```

---

## STEP 9 — Submit on Innovation Studio

| Field | Value |
|---|---|
| Project Name | ARGUS — Agentic Risk & Governance Unified Screening |
| Track | Reasoning Agents |
| IQ Layer | Foundry IQ |
| Foundry IQ Badge Evidence | https://globalai.community/badges/b35714f6-9372-4716-985f-ad2058722e76/ |
| GitHub | https://github.com/iarjunganesh/argus |
| Demo Video | https://youtu.be/YOUR_VIDEO_ID |

**Description:**
```
ARGUS is a multi-agent KYC risk assessment system built on Azure AI Foundry
using the A2A protocol. Four specialist agents run in parallel — Identity,
Screening, Corporate Intelligence, and Transaction Intelligence — and the
Compliance agent runs as the fan-in step coordinated by a central Orchestrator.

Foundry IQ powers three knowledge bases (regulatory text, sanctions, adverse
media), ensuring every risk decision includes cited, auditable references to
FATF recommendations and AML directives. An Explainability Agent generates a
plain-English narrative explaining WHY each entity received its risk rating.

Customer and transaction data are synthetic. Public-source adverse-media summaries are included for realistic screening citations.
```

**Deadline: June 14, 2026 — 11:59 PM Pacific Time**

---

## Time estimate

| Step | Time |
|---|---|
| 1 — Confidence score in UI | 15 min |
| 2 — Timestamped timeline | 20 min |
| 3 — README polish | 30 min |
| 4 — Foundry IQ knowledge bases | 45 min |
| 5 — OCR test + decision | 20 min |
| 6 — Record three scenarios | 20 min |
| 7 — Combine audio + video | 15 min |
| 8 — Upload + README update | 10 min |
| 9 — Submit | 10 min |
| **Total** | **~2 hrs 45 min** |
