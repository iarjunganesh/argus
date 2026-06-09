# ARGUS_FINAL_DEMO_RUNBOOK.md

## Microsoft Agents League 2026

### Reasoning Agents Track

### Final Submission Demo Runbook (Freeze Version)

Target Runtime: 4:20–4:50

Maximum Runtime: 5:00

---

# Recording Workflow

1. Record screen first
2. Generate voice-over separately using ElevenLabs
3. Merge audio and video
4. Export final video at 1080p

Recommended OBS Settings:

* Resolution: 1920x1080
* FPS: 30
* Cursor: Visible

Mouse Guidance:

* Move deliberately
* Click confidently
* Pause frequently

Avoid:

* Rapid scrolling
* Excessive cursor movement
* Hovering unnecessarily
* Switching tabs repeatedly

---

# Browser Tabs

Prepare before recording:

1. ARGUS Architecture Diagram
2. GitHub Repository README
3. ARGUS Gradio Application

Before recording:

* Close all notifications
* Close unnecessary tabs
* Log into required services
* Ensure no login screens appear

---

# AUDIO + VIDEO TIMELINE

| Time      | Audio                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Video                                                                                                     |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 0:00–0:30 | Know Your Customer investigations are essential for financial institutions, but they are often slow, expensive, and highly manual. Analysts must verify identities, investigate ownership structures, screen sanctions and watchlists, review adverse media, and assess transaction risks before making a compliance decision. ARGUS addresses this challenge using Microsoft Foundry and a team of specialized AI agents that collaborate through the Agent-to-Agent protocol to automate and explain the KYC investigation process. | Opening slide with ARGUS logo, title, tagline, and problem statement. No mouse movement.                  |
| 0:30–1:10 | At the center of ARGUS is an orchestrator agent responsible for coordinating a team of specialist compliance agents. The Identity Agent validates customer and entity information. The Screening Agent performs sanctions, watchlist, and adverse media checks. The Corporate Agent analyzes ownership structures and beneficial ownership relationships. The Transaction Agent evaluates transaction patterns and behavioral risks. The Compliance Agent consolidates findings and produces a final compliance assessment.           | Architecture diagram. Slowly highlight orchestrator and specialist agents.                                |
| 1:10–1:30 | Rather than relying on a single AI assistant, ARGUS decomposes complex investigations into specialized tasks and distributes them across multiple agents. Each agent reasons independently within its domain, and the orchestrator synthesizes the results into a unified assessment. This multi-agent approach improves transparency, explainability, reliability, and auditability while reducing investigation time.                                                                                                               | Continue architecture diagram.                                                                            |
| 1:30–1:35 | Before we begin, here's the ARGUS repository.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Brief GitHub README view.                                                                                 |
| 1:35–2:05 | Let's see ARGUS in action. Here, we're submitting a KYC investigation request. The orchestrator distributes work to specialist agents, which independently analyze identity, screening, ownership, transaction, and compliance risks before returning structured findings.                                                                                                                                                                                                                                                            | Switch to Gradio. Submit Cayman Synth Capital investigation.                                              |
| 2:05–2:30 | As the investigation progresses, ARGUS performs identity verification, screening analysis, ownership assessment, transaction risk evaluation, and compliance review in parallel. Findings from specialist agents are continuously aggregated into a unified compliance assessment.                                                                                                                                                                                                                                                    | Show investigation running and generation of report.                                                      |
| 2:30–2:50 | ARGUS has completed the investigation and assigned the risk rating shown on screen. Let's examine why.                                                                                                                                                                                                                                                                                                                                                                                                                                     | Pause on ARGUS Decision card. Allow judges to read Risk Tier, Risk Score, Confidence, and Recommendation. |
| 2:50–3:15 | The Executive Decision summarizes the overall assessment, confidence score, and recommended action. Directly beneath it, ARGUS explains why the rating was assigned by highlighting the primary risk drivers identified during the investigation.                                                                                                                                                                                                                                                                                     | Focus on ARGUS Decision card and Why This Risk Rating section.                                            |
| 3:15–3:35 | ARGUS also exposes operational transparency metrics including the number of agents invoked, tool calls executed, Foundry IQ queries when available, and total investigation runtime.                                                                                                                                                                                                                                                                                                                                                  | Show Agent Metrics panel and Foundry IQ Grounded badge.                                                   |
| 3:35–3:55 | Risk is evaluated across multiple dimensions including identity, screening, corporate ownership, transaction activity, and compliance exposure. This provides a structured view of where risk originates.                                                                                                                                                                                                                                                                                                                             | Show Risk Dimensions section.                                                                             |
| 3:55–4:10 | The investigation timeline provides a complete audit trail showing how specialist agents collaborated throughout the assessment.                                                                                                                                                                                                                                                                                                                                                                                                      | Show Investigation Timeline.                                                                              |
| 4:10–4:30 | Every recommendation is supported by evidence, key findings, regulatory triggers, and available regulatory grounding sources. When Foundry IQ citations are available, they are surfaced directly within the investigation report. This enables compliance analysts to understand and defend every recommendation produced by the system.                                                                                                                                                                                            | Show Key Findings, Regulatory Triggers, Foundry IQ citations, and Recommended Actions.                    |
| 4:30–4:50 | ARGUS demonstrates how Microsoft Foundry-powered reasoning agents can automate compliance investigations through orchestration, multi-step reasoning, explainability, regulatory grounding, evidence-based decision making, and auditability. By combining specialized agents, regulatory intelligence, and transparent risk assessment, ARGUS transforms a traditionally manual compliance process into a workflow completed in seconds. Thank you for watching.                                                                     | Closing slide with logo, Foundry reference, and project summary.                                          |

---

# Opening Slide

Logo:
assets/argus.svg

Display:

ARGUS

Agentic Risk & Governance Unified Screening

Multi-Agent Compliance Intelligence

Microsoft Agents League 2026

Reasoning Agents Track

---

# Closing Slide

Logo:
assets/argus.svg

Display:

ARGUS

Built with Microsoft Foundry

Multi-Agent Compliance Intelligence

Reasoning Agents Track

Thank You

---

# Key Screens To Capture

1. Architecture Diagram
2. GitHub Repository README
3. Investigation Submission
4. ARGUS Decision Card
5. Why This Risk Rating
6. Agent Metrics
7. Foundry IQ Grounded Badge
8. Risk Dimensions
9. Investigation Timeline
10. Key Findings
11. Regulatory Triggers (Foundry IQ cited)
12. Recommended Actions
13. Closing Slide

---

# Visual Priority Order

When screen space is limited, focus in this order:

1. ARGUS Decision
2. Why This Risk Rating
3. Agent Metrics
4. Foundry IQ Grounded
5. Risk Dimensions
6. Investigation Timeline
7. Key Findings
8. Regulatory Triggers
9. Recommended Actions

OCR demo guidance: Keep OCR collapsed during recording. Mention it briefly as a capability, but prioritize decision, explainability, multi-agent metrics, timeline, and regulatory grounding.

---

# Final Submission Checklist

## Product

* Verify ARGUS Decision Card
* Verify Why This Risk Rating
* Verify Agent Metrics
* Verify Foundry IQ Badge
* Verify Risk Dimensions
* Verify Investigation Timeline
* Verify Regulatory Triggers
* Verify Recommended Actions

## Assets

* Logo
* README

## Recording

* Screen Recording
* ElevenLabs Voice-over
* Audio Sync
* Video Export
* Final Review

---

# Do Not Build

* MCP Integration
* GraphRAG
* Additional Agents
* Additional Azure Services
* Major Refactoring
* OCR Redesign
* Perpetual KYC Features

These are post-hackathon roadmap items.

---

# Final Message For Judges

ARGUS is an AI Compliance Analyst powered by Microsoft Foundry. Using specialized reasoning agents coordinated through an orchestrator, ARGUS investigates customers and businesses, gathers supporting evidence, evaluates risk across multiple dimensions, grounds recommendations using Foundry IQ knowledge sources, and produces transparent, explainable, and auditable compliance decisions in seconds.
