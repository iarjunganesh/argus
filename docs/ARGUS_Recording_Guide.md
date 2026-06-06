# ARGUS — Demo Recording Session Guide
## Do everything in this exact order.

---

## PHASE 1: SETUP (do the day before)

### 1.1 Install OBS Studio
- Download from obsproject.com
- Install with default settings
- Open OBS once to confirm it works

### 1.2 Install Clipchamp (video editor — free, Windows built-in)
- Search "Clipchamp" in Windows Start menu
- If not installed: microsoft.com/en-us/microsoft-365/clipchamp
- Mac users: use iMovie (already installed)

### 1.3 Generate ElevenLabs audio
1. Go to elevenlabs.io → Sign up free
2. Click "Speech Synthesis"
3. Select voice: **Rachel**
4. Speed: **1.0x** (do not change)
5. Open ARGUS_Demo_Script.txt
6. Copy ONLY the spoken lines (not the [SECTION] labels, not the dashes)
7. Paste into ElevenLabs text box
8. Click Generate
9. Click Download → save as **argus_voiceover.mp3**

### 1.4 Prepare your screen
- Set display resolution to **1920 × 1080**
- Set browser zoom to **125%** (Ctrl + Plus twice)
- Close all unnecessary applications
- Turn off notifications (Windows: Focus Assist ON / Mac: Do Not Disturb ON)

---

## PHASE 2: PRE-RECORDING TEST RUN

### 2.1 Start the API (Terminal 1)
```bash
cd argus
python -m uvicorn api.main:app --port 8000
```
Wait until you see: `Application startup complete`

### 2.2 Start the Gradio UI (Terminal 2)
```bash
cd argus
python ui/gradio_app.py
```
Wait until you see: `Running on local URL: http://0.0.0.0:7860`

### 2.3 Open browser tabs in this order
- Tab 1: http://localhost:7860 (Gradio UI — this is your main demo tab)
- Tab 2: github.com/iarjunganesh/argus (for closing shot)
- Tab 3: github.com/iarjunganesh/argus/blob/main/architecture/ARGUS_Architecture.md (for opening shot)

### 2.4 Do a test submission (do NOT record yet)
- In Tab 1 (Gradio), enter:
  - Entity Name: `Cayman Synth Capital`
  - Entity Type: `corporate`
  - Jurisdiction: `KY`
- Click Submit
- Wait for the report to appear
- Scroll through the full report — make sure it all looks correct
- This confirms everything is working before you record

---

## PHASE 3: OBS SETUP

### 3.1 Configure OBS
1. Open OBS Studio
2. Under Sources → click `+` → select `Display Capture` → click OK
3. Click Settings (bottom right)
4. Go to Output tab:
   - Output Mode: Simple
   - Recording Quality: High Quality, Medium File Size
   - Recording Format: mp4
5. Go to Video tab:
   - Base Resolution: 1920×1080
   - Output Resolution: 1920×1080
   - FPS: 30
6. Click OK

### 3.2 Audio settings
- You do NOT need a microphone (AI voiceover)
- In OBS: right-click Mic/Aux → Properties → set to Disabled
- Only Desktop Audio should be enabled (or also disable it — no sound needed in recording)

---

## PHASE 4: RECORDING SESSION

### Start recording when you are ready. Follow this sequence exactly.

---

**[0:00] START OBS RECORDING**
- In OBS: click `Start Recording`
- Wait 3 seconds before moving your mouse

---

**[0:00 – 0:30] Show architecture diagram**
- Switch to Tab 3 (architecture/ARGUS_Architecture.md on GitHub)
- Scroll slowly so the ASCII architecture diagram is fully visible
- Stay on this screen for ~30 seconds

---

**[0:30 – 1:30] Keep architecture visible**
- Scroll up to show the full README architecture section
- You can also show the Agent table (Identity, Screening, Corporate, Compliance, Transaction)
- Move mouse slowly and deliberately — no fast movements

---

**[1:30] Switch to Gradio UI**
- Click Tab 1 (localhost:7860)
- The UI should be clean and empty

---

**[1:45] Type the KYC request — type slowly**
- Click Entity Name field → type: `Cayman Synth Capital`
- Click Entity Type dropdown → select: `corporate`
- Click Jurisdiction field → type: `KY`

---

**[2:00] Click Submit**
- Click the Submit button
- Move your mouse away from the button after clicking
- Wait — do not click anything

---

**[2:10 – 2:30] Show processing state**
- Let the report load naturally
- If it takes more than 30 seconds, that is fine — the voiceover covers this time

---

**[2:30] Report appears — scroll slowly**
- Scroll down slowly to show the full risk report
- Pause on the coloured risk tier banner (HIGH / MEDIUM / etc.)
- Continue scrolling to the dimension scores table

---

**[2:45 – 3:30] Show Foundry IQ citations**
- Scroll to the "Regulatory Triggers" section
- Move mouse to hover over a citation line
- Stay here for ~30 seconds so viewers can read it

---

**[3:30 – 4:20] Walk through risk report**
- Scroll to dimension scores — pause on each score briefly
- Scroll to Recommended Actions
- Scroll to Audit Trace at the bottom
- Hover mouse over "foundry_iq_queries: 3" line

---

**[4:30] Switch to GitHub repo**
- Click Tab 2 (github.com/iarjunganesh/argus)
- Scroll slowly to show the README — badges, architecture, agent table
- End with the repo URL visible at the top of the browser

---

**[5:00] STOP OBS RECORDING**
- In OBS: click `Stop Recording`
- Wait for OBS to finish writing the file
- Find the recording in your Videos folder

---

## PHASE 5: COMBINE AUDIO + VIDEO

### Using Clipchamp (Windows)
1. Open Clipchamp → New Video
2. Import the OBS recording → drag it to the timeline
3. Import argus_voiceover.mp3 → drag it below the video track
4. Right-click the video track → click Mute (removes any screen noise)
5. Play from the beginning — check audio and video are roughly in sync
6. If the audio ends before the video: trim the last few seconds of video
7. If the video ends before the audio: extend the last frame (or trim audio)
8. Export → 1080p → Export

### Using iMovie (Mac)
1. Open iMovie → New Movie
2. Import both files
3. Drag OBS recording to timeline
4. Drag argus_voiceover.mp3 to the timeline below the video
5. Right-click video → Detach Audio → delete the detached audio track
6. File → Share → File → 1080p → Export

---

## PHASE 6: UPLOAD TO YOUTUBE

1. Go to youtube.com → click Upload (camera icon, top right)
2. Select your exported MP4
3. Title: `ARGUS — Agentic KYC Risk Assessment | Microsoft Agents League Hackathon 2026`
4. Description:
```
ARGUS (Agentic Risk & Governance Unified Screening) — a multi-agent KYC system
built on Azure AI Foundry with Foundry IQ knowledge retrieval.

5 parallel A2A agents | 15 tools | 3 Foundry IQ knowledge bases | GPT-4o reasoning

Microsoft Agents League Hackathon 2026 — Reasoning Agents Track

GitHub: https://github.com/iarjunganesh/argus

All data is 100% synthetic. No real PII or financial data.
```
5. Visibility: **Unlisted** (judges can access via link, not publicly searchable)
6. Click Save
7. Copy the video URL from the browser

---

## PHASE 7: FINAL UPDATES

### Update README with video link
```bash
cd argus
# Edit README.md — find this line:
# 📹 [Demo Video](https://youtube.com/TODO)
# Replace with:
# 📹 [Demo Video](https://youtu.be/YOUR_VIDEO_ID)

git add README.md
git commit -m "docs: add demo video link"
git push
```

### Done. Submit on Innovation Studio before June 14, 11:59 PM PT.

---

## Quick troubleshooting

| Problem | Fix |
|---|---|
| Gradio UI not loading | Check API is running first (Terminal 1) |
| Report takes too long | Normal — mock fallbacks can be slow. Pre-run before recording. |
| OBS recording is laggy | Lower OBS bitrate to 4000 kbps in Settings |
| Audio and video out of sync | In editor, nudge the MP3 track left or right by 1-2 seconds |
| ElevenLabs audio cuts off early | Re-generate — sometimes it clips. Download again. |
