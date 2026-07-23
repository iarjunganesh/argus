---
title: "ARGUS: Compliance Infrastructure That Believes Financial Access Is a Human Right"
tags: Azure AI Foundry, Semantic Kernel, Multi-Agent Systems, Foundry IQ, Hack for Good, Financial Inclusion
---

A refugee family in Germany spends 18 months trying to open a bank account. Their documents are legitimate. But an automated KYC system — never designed with them in mind — scores their jurisdiction as high risk and closes the case. No human review. No plain-language explanation. No appeal path.

An NGO doing legitimate microfinance work in Southeast Asia gets de-risked by their correspondent bank. The letter cites "risk appetite." The lending operation, which supports 4,000 families, can no longer move money.

These aren't edge cases. **1.4 billion people remain financially excluded globally** — and compliance systems built to protect institutions are a leading cause. The same technology meant to stop financial crime routinely shuts out the people who most need access.

That's the problem I set out to fix with **ARGUS** (Agentic Risk & Governance Unified Screening) at the Microsoft Agents League — AI Skills Fest 2026, where it was selected as **1 of 3 Hack for Good winners** — awarded to the best solutions to solve a community need.

## What ARGUS does

ARGUS is compliance infrastructure that is explainable, accessible, and open — designed from the ground up for the humans most likely to be failed by the systems they depend on, not just for the institutions running the checks.

A single KYC request fans out across **five specialist AI agents**, coordinated via the **Agent-to-Agent (A2A) protocol** on **Azure AI Foundry**:

- 🎯 **Orchestrator Agent** — task decomposition and result synthesis
- 🪪 **Identity Agent** — customer lookup, OCR processing, identity validation
- 🔍 **Screening Agent** — sanctions checks, adverse media scanning, PEP checks
- 🏢 **Corporate Intelligence Agent** — UBO resolution, registry lookups, jurisdiction mapping
- 💳 **Transaction Intelligence Agent** — transaction monitoring, pattern detection, typology matching

Each of these fans back into a **Compliance & Risk Agent**, which synthesizes everything into a single traceable risk report.

The part I'm proudest of: nothing in that report is a black box. Every finding is grounded in cited regulatory knowledge via **Foundry IQ** — sanctions checks and regulatory triggers cite the exact knowledge base, source document, and article behind them. Every risk score comes with a plain-English reason. Every decision leaves a full audit trail: agent by agent, tool by tool, citation by citation.

```
Submit entity → 5 agents run in parallel → Compliance fan-in → Traceable risk report
```

📹 [Watch the 5-minute demo](https://youtu.be/yaTNCgCwX4s)

## What's next: ARGUS v2

The hackathon build proved the architecture holds up. The v2 roadmap is where it grows into something NGOs and microfinance institutions can actually run:

| Feature | Status |
|---|---|
| ♿ Full WCAG 2.1 AA compliance | In progress |
| 🗣 Explain Mode — plain-language reports for the person being screened | In progress |
| 🌍 Community Edition — free, self-hostable, zero Azure subscription required | Designed |
| 📊 Real-time Azure Monitor compliance dashboard | Designed |
| 🔓 Open Knowledge Graph — FATF, Basel AML Index, OFAC/EU/UN lists as open data | Planned |

**Explain Mode** is the one I'd highlight for an educator audience. Today's report is written for compliance analysts:

> *"Dimension score 78 — HIGH tier — regulatory trigger: FATF Recommendation 16 (KB-Regulations › FATF-40 › R.16)"*

Explain Mode generates the same finding for the person being screened, or the NGO caseworker who has to explain a decision to a family:

> *"This account review flagged a potential concern with how money moved through the transaction chain. This is a standard check for large or cross-border transfers. A compliance officer will review this before a final decision is made. You don't need to do anything right now."*

Same underlying data. Entirely different outcome for the person on the receiving end.

**Community Edition** is the biggest bet: a zero-cost, self-hostable configuration for NGOs, microfinance institutions, community banks, and researchers — a pre-seeded public knowledge base, a one-command Docker Compose stack, and a lower-cost LLM path, so an Azure subscription isn't a prerequisite for the core flow.

## Try it yourself

ARGUS is open source under MIT. If you're teaching agentic AI, Azure AI Foundry, or Semantic Kernel, the repo is built to be a working example of multi-agent orchestration with A2A and grounded retrieval via Foundry IQ:

```bash
git clone https://github.com/iarjunganesh/argus.git
cd argus
pip install -r requirements.txt
cp .env.example .env
make generate-data && make generate-ocr-docs
make index-knowledge-bases
.\scripts\start_demo.ps1
```

The Community Edition — no Azure subscription required — is scaffolded in [`community/`](https://github.com/iarjunganesh/argus/tree/main/community) as part of the v2 roadmap, but isn't runnable yet.

The most-needed contributions right now are WCAG contrast tests for the Gradio UI, translations of Explain Mode output, and finishing the Community Edition Docker Compose stack (Dockerfile + local knowledge base seed) — all good starter issues for students exploring accessible AI system design.

**Repo:** https://github.com/iarjunganesh/argus
**Demo video:** https://youtu.be/yaTNCgCwX4s

*ARGUS is a technology demonstration and is not a licensed compliance tool — it must not be used to make real KYC/AML decisions.*
