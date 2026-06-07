# ARGUS — Final Steps to Submission
### June 13 → June 14, 11:59 PM PT

> Archived planning note: superseded by docs/ARGUS_PreSubmission_Steps.md.
> This file is kept for historical context and should not be used as the active runbook.

---

## STEP 1 — Clean the repo (5 min)

```bash
# Delete local noise files
rm -f data/dry_run_batch.jsonl
rm -f data/live_wiring_check.jsonl
rm -f data/reports_batch_errors.jsonl

# Move planning doc into docs/
mv ARGUS_NextSteps_June8-14.md docs/

# Add to .gitignore so batch outputs never get committed
echo "data/*.jsonl" >> .gitignore

# Commit
git add .gitignore docs/ARGUS_NextSteps_June8-14.md
git commit -m "chore: clean artifacts, move planning doc to docs/, update gitignore"
git push
```

---

## STEP 2 — GitHub topics (2 min)

1. Go to **github.com/iarjunganesh/argus**
2. Click the **⚙️ gear icon** next to About (top right of file list)
3. Add these topics one by one:

```
azure-ai-foundry
foundry-iq
kyc
aml
multi-agent
a2a-protocol
semantic-kernel
compliance
hackathon-2026
gpt-4o
```

4. Click **Save changes**

---

## STEP 3 — Pre-recording (do before opening OBS)

### Start all agents — one terminal each

```bash
# Terminal 1
python -m uvicorn api.main:app --port 8000

# Terminal 2
python -m uvicorn agents.identity.agent:app --port 8001

# Terminal 3
python -m uvicorn agents.screening.agent:app --port 8002

# Terminal 4
python -m uvicorn agents.corporate.agent:app --port 8003

# Terminal 5
python -m uvicorn agents.compliance.agent:app --port 8004

# Terminal 6
python -m uvicorn agents.transaction.agent:app --port 8005

# Terminal 7
python ui/gradio_app.py
```

### Health check — all must say "ok"

```bash
python -c "
import httpx
agents = [(8001,'identity'),(8002,'screening'),(8003,'corporate'),
          (8004,'compliance'),(8005,'transaction')]
for port, name in agents:
    try:
        r = httpx.get(f'http://127.0.0.1:{port}/health', timeout=2)
        print(f'{name}: {r.json()[\"status\"]}')
    except Exception as e:
        print(f'{name}: UNREACHABLE — restart terminal')
"
```

### Test run (do NOT record yet)

1. Open browser → **http://localhost:7860**
2. Submit: `Cayman Synth Capital` / `corporate` / `KY`
3. Wait for full report to load
4. Confirm these four sections appear:
   - ✅ Risk tier banner (HIGH, red)
   - ✅ 🧠 Explanation panel (blue, plain English text)
   - ✅ Risk Dimensions table (score bars)
   - ✅ Agent Activity section (all 5 = done)
5. If anything is missing — fix before recording

### Screen setup

```
□ Browser zoom: 125% (Ctrl + Plus twice)
□ Browser tabs open:
    Tab 1: http://localhost:7860           ← main demo
    Tab 2: github.com/iarjunganesh/argus   ← closing shot
    Tab 3: github.com/iarjunganesh/argus/blob/main/architecture/ARGUS_Architecture.md ← opening shot
□ Notifications OFF (Windows: Focus Assist ON)
□ All other apps closed
□ Display resolution: 1920×1080
```

---

## STEP 4 — OBS setup (5 min)

1. Open **OBS Studio**
2. Sources → `+` → **Display Capture** → OK
3. Settings → Output tab:
   - Output Mode: `Simple`
   - Recording Quality: `High Quality, Medium File Size`
   - Format: `mp4`
4. Settings → Video tab:
   - Base Resolution: `1920×1080`
   - Output Resolution: `1920×1080`
   - FPS: `30`
5. Audio → right-click Mic/Aux → **Disable** (no mic needed)
6. Click OK

---

## STEP 5 — Recording sequence

**Click Start Recording in OBS. Then follow this order exactly.**

| Time | Screen | Action |
|---|---|---|
| 0:00 | Tab 3 — Architecture.md on GitHub | Stay still — let voiceover play |
| 0:30 | Tab 3 | Scroll slowly to agent table |
| 1:30 | Tab 1 — Gradio UI | Switch tab |
| 1:45 | Gradio — Entity Name field | Type: `Cayman Synth Capital` slowly |
| 1:52 | Gradio — Entity Type | Select: `corporate` |
| 1:55 | Gradio — Jurisdiction | Type: `KY` |
| 2:00 | Gradio — Submit button | Click — then move mouse away |
| 2:10 | Gradio — wait | Do not click anything |
| 2:30 | Report — risk tier banner | Scroll to it — pause 5 sec |
| 2:40 | Report — 🧠 Explanation panel | Scroll to it — pause 10 sec |
| 3:00 | Report — Regulatory Triggers | Scroll to it — pause 10 sec |
| 3:30 | Report — Risk Dimensions table | Scroll to it — show bars |
| 3:45 | Report — Agent Activity | Scroll to it — show all done |
| 4:00 | Report — Recommended Actions | Scroll to it |
| 4:20 | Report — Full JSON | Click to expand — show audit trace |
| 4:30 | Tab 2 — GitHub repo | Switch tab |
| 4:45 | GitHub README | Scroll slowly |
| 5:00 | — | **Stop Recording in OBS** |

---

## STEP 6 — Combine audio and video (15 min)

### Open Clipchamp (Windows) or iMovie (Mac)

**Clipchamp:**
1. New Video
2. Import OBS recording → drag to timeline
3. Import `argus_voiceover.mp3` → drag below video track
4. Right-click video track → **Mute**
5. Play from start — check sync
6. If audio ends before video: trim last seconds of video
7. Export → **1080p**

**iMovie:**
1. New Movie
2. Import both files
3. Drag recording to timeline
4. Drag MP3 below video
5. Right-click video → Detach Audio → delete detached track
6. File → Share → File → **1080p** → Export

---

## STEP 7 — Upload to YouTube (5 min)

1. Go to **youtube.com** → Upload (camera icon, top right)
2. Select exported MP4
3. Fill in:

**Title:**
```
ARGUS — Agentic KYC Risk Assessment | Microsoft Agents League Hackathon 2026
```

**Description:**
```
ARGUS (Agentic Risk & Governance Unified Screening) is a multi-agent KYC
compliance system built on Azure AI Foundry.

4 parallel specialist agents + 1 compliance fan-in step · 15 tools · Foundry IQ (3 knowledge bases) · GPT-4o

Microsoft Agents League Hackathon 2026 — Reasoning Agents Track

GitHub: https://github.com/iarjunganesh/argus

All data is 100% synthetic. No real PII or financial data used.
```

4. Visibility: **Unlisted**
5. Click **Save**
6. Copy the video URL from the browser bar

---

## STEP 8 — Update README + final push (5 min)

```bash
# Edit README.md — find this line:
# 📹 [Demo Video](https://youtube.com/TODO)
# Replace with your actual YouTube link:
# 📹 [Demo Video](https://youtu.be/YOUR_VIDEO_ID)

git add README.md
git commit -m "docs: add demo video link — submission ready"
git push
```

---

## STEP 9 — Submit on Innovation Studio

1. Go to the hackathon portal
2. Click **Projects** → **Submit Project**
3. Fill in:

| Field | Value |
|---|---|
| Project Name | ARGUS — Agentic Risk & Governance Unified Screening |
| Track | Reasoning Agents |
| IQ Layer Used | Foundry IQ |
| GitHub URL | https://github.com/iarjunganesh/argus |
| Demo Video | https://youtu.be/YOUR_VIDEO_ID |

**Description to paste:**
```
ARGUS is a multi-agent KYC risk assessment system built on Azure AI Foundry
using the Agent-to-Agent (A2A) protocol. A single compliance request is
decomposed into 5 specialist agents running in parallel: Identity, Screening,
Corporate Intelligence, Transaction Intelligence, and Compliance & Risk.

The Foundry IQ intelligence layer powers 3 knowledge bases — regulatory text
(FATF/4AMLD/6AMLD), sanctions data, and adverse media — ensuring every risk
decision includes cited, grounded, hallucination-resistant references.

An Explainability Agent generates plain-English narratives explaining WHY each
entity received its risk rating — making reasoning visible to judges and
compliance officers alike. All data is 100% synthetic.
```

4. Click **Submit**

---

## ⏰ Deadline: June 14, 2026 — 11:59 PM Pacific Time

---

## Quick troubleshooting

| Problem | Fix |
|---|---|
| Agent shows UNREACHABLE | Restart that terminal — check for import errors |
| Report comes back empty | Check compliance agent logs for errors |
| Explanation panel missing | Confirm `explain_decision` is imported in compliance/agent.py |
| Gradio won't load | Check API is running first on port 8000 |
| OBS recording is laggy | Lower bitrate to 4000 kbps in Settings → Output |
| Audio and video out of sync | Nudge MP3 track left/right by 1–2 seconds in editor |
| YouTube link is wrong | Re-copy from browser bar — must start with youtu.be or youtube.com |
