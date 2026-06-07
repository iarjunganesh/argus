# ARGUS — Agentic Risk & Governance Unified Screening

> **Microsoft Agents League Hackathon 2026 — Reasoning Agents Track**

[![Azure AI Foundry](https://img.shields.io/badge/Azure%20AI%20Foundry-Agent%20Service-0078D4)](https://ai.azure.com)
[![Foundry IQ](https://img.shields.io/badge/Microsoft%20IQ-Foundry%20IQ-7B2FBE)](https://github.com/microsoft/iq-series)
[![A2A](https://img.shields.io/badge/Pattern-Agent--to--Agent-00B4D8)](https://aka.ms/a2a)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB)](https://python.org)

---

## What is ARGUS?

ARGUS is an open, multi-agent KYC (Know Your Customer) risk assessment system that demonstrates enterprise-grade agentic reasoning applied to financial compliance.

A single KYC request is decomposed into **4 parallel specialist agents plus a compliance fan-in step** coordinated via the **Agent-to-Agent (A2A)** protocol on **Azure AI Foundry**. Knowledge retrieval is powered by **Foundry IQ** — providing cited, grounded, hallucination-resistant answers from regulatory knowledge bases.

**All data is 100% synthetic. No real PII or financial data is used.**

---

## The Problem

KYC compliance requires a human analyst to simultaneously verify identity,
screen sanctions lists, resolve corporate ownership structures, and assess
regulatory risk. Done manually, this takes 2-5 days per customer and costs
financial institutions billions in compliance overhead annually. A missed
risk can result in multi-million dollar regulatory fines.

## How ARGUS Works

1. Submit an entity name, type, and jurisdiction
2. ARGUS fans out to Identity, Screening, Corporate, and Transaction agents in parallel via the A2A protocol
3. Foundry IQ retrieves cited, grounded answers from regulatory knowledge bases
4. Compliance agent runs as the fan-in step and synthesises a weighted risk score, confidence, plain-English explanation, and action plan
5. Every decision is fully traceable - agent by agent, tool by tool, citation by citation

## Architecture

```mermaid
graph TD
     Client([Client / UI]) -->|KYC Request| ORC

     ORC[🎯 Orchestrator Agent<br/>Task Decomposition &<br/>Result Synthesis]

     ORC -->|A2A call| IDA[🪪 Identity Agent]
     ORC -->|A2A call| SCA[🔍 Screening Agent]
     ORC -->|A2A call| CIA[🏢 Corporate Intelligence Agent]
     ORC -->|A2A call| TIA[💳 Transaction Intelligence Agent]

     IDA -->|identity_result| ORC
     SCA -->|screening_result| ORC
     CIA -->|corporate_result| ORC
     TIA -->|transaction_result| ORC

     ORC -->|fan-in: all results| CRA[⚖️ Compliance & Risk Agent]
     CRA -->|compliance_result| ORC
     ORC -->|Risk Report| Client

     IDA --- T1[customer_lookup<br/>ocr_processor<br/>identity_validator]
     SCA --- T2[sanctions_checker 🧠<br/>adverse_media_scanner 🧠<br/>pep_checker]
     CIA --- T3[ubo_resolver<br/>registry_lookup<br/>jurisdiction_mapper]
     CRA --- T4[regulations_rag 🧠<br/>risk_scorer<br/>gap_analyzer]
     TIA --- T5[transaction_monitor<br/>pattern_detector<br/>typology_matcher]

     FIQ[🧠 Foundry IQ<br/>KB-Regulations<br/>KB-Sanctions<br/>KB-AdverseMedia]
     T2 -->|query| FIQ
     T4 -->|query| FIQ
```

> 🧠 = Foundry IQ powered tool

See [architecture/ARGUS_Architecture.md](architecture/ARGUS_Architecture.md) for the full spec.

---

## Challenge Tracks

| Track | Prize Target |
|---|---|
| 🧠 Reasoning Agents | Best Reasoning Agent |
| 💡 Microsoft IQ | Best Use of IQ Tools (Foundry IQ × 3 KBs) |

---

## Agents

| Agent | Tools | Foundry IQ |
|---|---|---|
| 🎯 Orchestrator | A2A coordination | — |
| 🪪 Identity | customer_lookup, ocr_processor, identity_validator | — |
| 🔍 Screening | sanctions_checker, adverse_media_scanner, pep_checker | ✅ KB-Sanctions, KB-AdverseMedia |
| 🏢 Corporate Intelligence | ubo_resolver, registry_lookup, jurisdiction_mapper | — |
| ⚖️ Compliance & Risk | regulations_rag, risk_scorer, gap_analyzer | ✅ KB-Regulations |
| 💳 Transaction Intelligence | transaction_monitor, pattern_detector, typology_matcher | — |

---

## Tech Stack

- **Azure AI Foundry Agent Service** — agent hosting + A2A
- **Foundry IQ** — knowledge retrieval (Regulations, Sanctions, Adverse Media)
- **Semantic Kernel** — A2A orchestration
- **Azure OpenAI** (GPT-4o) — reasoning
- **Azure Document Intelligence** — OCR for identity documents
- **Azure Cosmos DB** — synthetic entity/transaction data
- **Azure AI Search** — backing store for Foundry IQ KBs
- **FastAPI** — REST API gateway
- **Gradio** — demo UI

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/iarjunganesh/argus.git
cd argus

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in your Azure credentials

# 4. Generate synthetic data
make generate-data

# 5. Index into Foundry IQ
make index-knowledge-bases

# 6. Run the API
make run-api

# 7. Start all specialist agents (separate terminals)
make run-identity-agent
make run-screening-agent
make run-corporate-agent
make run-compliance-agent
make run-transaction-agent

# 8. Launch demo UI
make run-ui
```

## Demo & Testing

We've included a demo runbook and a batch-run script to produce sample KYC reports:

- Docs index: docs/README.md
- Demo runbook: docs/DEMO_RUNBOOK.md
- Batch KYC runner: scripts/batch_run_kyc.py

Run the batch runner to create 10 sample reports (saved to data/reports_batch.jsonl):

```powershell
python scripts/batch_run_kyc.py --count 10 --out data/reports_batch.jsonl --poll-timeout 180
```

For stable batch execution, run the API without `--reload` to avoid hot-reload interrupts:

```powershell
python -m uvicorn api.main:app --port 8000
```

Failed batch items are written to `data/reports_batch_errors.jsonl` while successful reports are written to `data/reports_batch.jsonl`.

Logs are emitted in JSON format by all services (see utils/structured_logger.py).

---

## Demo

📹 [Demo Video](https://youtube.com/TODO) *(updated on submission day)*

### Demo Scenarios

| Scenario | Entity | Type | Jurisdiction | Expected Outcome |
|---|---|---|---|---|
| 🔴 High Risk | `Cayman Synth Capital` | corporate | KY | HIGH - Enhanced Due Diligence |
| 🟠 Medium Risk | `Synthetic Holdings B.V.` | corporate | NL | MEDIUM - Elevated monitoring |
| 🟢 Low Risk | `Jane Synthetic` | individual | DE | LOW - Standard onboarding |

For recording and narration assets, use:

- docs/ARGUS_Recording_Guide.md
- docs/ARGUS_Demo_Script.txt
- docs/ARGUS_Demo_VoiceOver.txt

---

## Disclaimer

ARGUS is a technology demonstration built for a hackathon. It is not a licensed compliance tool and must not be used to make real KYC/AML decisions. All data is synthetic. No affiliation with any financial institution.
