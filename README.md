# ARGUS

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/brand/banner-light.svg">
    <img width="900" src="assets/brand/banner-light.svg" alt="ARGUS — Agentic Risk & Governance Unified Screening. Explainable KYC screening, built for the people automated compliance fails."/>
  </picture>
</p>

<p align="center">
  <strong>Compliance infrastructure that believes financial access is a human right.</strong>
</p>

<p align="center">
  <a href="https://techcommunity.microsoft.com/blog/educatordeveloperblog/%F0%9F%8F%86-agents-league-celebrating-the-builders-who-made-agents-battle-for-glory/4538007"><img alt="Microsoft Agents League — AI Skills Fest 2026 | Hack for Good winner (1 of 3)" src="https://img.shields.io/badge/🏆_Microsoft_Agents_League_—_AI_Skills_Fest_2026-Hack_for_Good_winner_(1_of_3)-gold?style=for-the-badge"/></a>
</p>

<p align="center">
  <a href="https://globalai.community/badges/8261feac-a6a6-4ee9-bc77-4ebecbbf2ce8"><img alt="Agents League — Reasoning Agents badge" src="https://globalai.community/img/badge/shared/e7860f511b05fc9a1a85b9335618871286c3279b000350d76b049f6049f2aa51.png?h=500" height="120"/></a>
  &nbsp;&nbsp;
  <a href="https://globalai.community/badges/b35714f6-9372-4716-985f-ad2058722e76"><img alt="The Microsoft IQ Series: Foundry IQ badge" src="https://globalai.community/img/badge/shared/f1de85c1359e1380dcabb9901d210a3d00645ec975a640338021f91792d26ffd.png?h=500" height="120"/></a>
</p>

<!-- Row 1 — repository state: these six, in this order.
     Nothing may be inserted between the badge lines of a row: a comment breaks the paragraph
     and drops the badge after it onto a row of its own.
     Release opens the latest release; until v0.1.0 is tagged GitHub shows the empty list. -->
[![CI](https://github.com/iarjunganesh/argus/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/iarjunganesh/argus/actions/workflows/ci.yml)
[![SonarQube Cloud](https://img.shields.io/sonar/quality_gate/iarjunganesh_argus?server=https%3A%2F%2Fsonarcloud.io&logo=sonarqubecloud&label=SonarQube%20Cloud)](https://sonarcloud.io/summary/new_code?id=iarjunganesh_argus)
[![Codecov](https://codecov.io/gh/iarjunganesh/argus/graph/badge.svg)](https://codecov.io/gh/iarjunganesh/argus)
[![Release](https://img.shields.io/badge/release-latest-2ea44f?logo=github&logoColor=white)](https://github.com/iarjunganesh/argus/releases/latest)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Watch Video](https://img.shields.io/badge/%E2%96%B6_Watch-5--min_demo-FF0000?logo=youtube&logoColor=white)](https://youtu.be/yaTNCgCwX4s)

<!-- Row 2 — the Microsoft framework and every Azure service ARGUS uses, and what each does.
     Fixed rules set the score and tier; the model only writes the explanation (no model is the
     default: a labelled template). The Azure services are optional: the local data plane, the
     default, needs none of them. -->
[![Microsoft Agent Framework](https://img.shields.io/badge/Agent_Framework-1.19.0-0078D4)](https://github.com/microsoft/agent-framework)
[![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-explanation_only-412991)](https://azure.microsoft.com/en-us/pricing/details/azure-openai/)
[![Foundry IQ](https://img.shields.io/badge/Foundry_IQ-cited_knowledge_bases-0078D4)](https://azure.microsoft.com/en-us/products/ai-foundry/iq)
[![Azure AI Search](https://img.shields.io/badge/Azure_AI_Search-knowledge_base_indexes-0078D4)](https://azure.microsoft.com/en-us/products/ai-services/ai-search)
[![Cosmos DB](https://img.shields.io/badge/Cosmos_DB-entities_and_reports-0078D4)](https://azure.microsoft.com/en-us/products/cosmos-db)
[![Document Intelligence](https://img.shields.io/badge/Document_Intelligence-document_OCR-0078D4)](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence)
[![Azure Container Apps](https://img.shields.io/badge/Azure_Container_Apps-API_host-0078D4)](https://azure.microsoft.com/en-us/products/container-apps)
[![Azure Monitor](https://img.shields.io/badge/Azure_Monitor-API_logs-0078D4)](https://azure.microsoft.com/en-us/products/monitor)

<!-- Row 3 — frontend (web/). Vercel Hobby is the chosen host (decision D1); not deployed yet. -->
[![Next.js](https://img.shields.io/badge/Next.js-16.3-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.3-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Node.js](https://img.shields.io/badge/Node.js-24-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4.3-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![shadcn/ui](https://img.shields.io/badge/shadcn%2Fui-Radix-000000?logo=shadcnui&logoColor=white)](https://ui.shadcn.com/)
[![Playwright](https://img.shields.io/badge/Playwright-1.63-2EAD33)](https://playwright.dev/)
[![axe](https://img.shields.io/badge/axe-4.13_WCAG_2.2_AA-663399)](https://github.com/dequelabs/axe-core)
[![Vercel Hobby](https://img.shields.io/badge/Vercel-Hobby-000000?logo=vercel&logoColor=white)](https://vercel.com/pricing)

<!-- Row 4 — backend and toolchain. -->
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.13_contracts-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![uv](https://img.shields.io/badge/uv-locked-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/badge/Ruff-lint%20%2B%20format-D7FF64?logo=ruff&logoColor=111827)](https://docs.astral.sh/ruff/)
[![Mypy](https://img.shields.io/badge/Mypy-type_checked-2A6DB2?logo=python&logoColor=white)](https://mypy-lang.org/)
[![pytest](https://img.shields.io/badge/pytest-9.1-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Docker](https://img.shields.io/badge/Docker-non--root,_digest--pinned-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tesseract](https://img.shields.io/badge/Tesseract-local_OCR-3C8DBC)](https://github.com/tesseract-ocr/tesseract)

<!-- Row 5 — the tier of each Azure service in row 2, as chosen in decision D1 (docs/ARCHITECTURE.md,
     "Hosting"). Nothing is deployed yet, and the Azure data plane has only run against SDK
     stand-ins. Each badge opens the service's pricing page. -->
[![Azure OpenAI tier](https://img.shields.io/badge/Azure_OpenAI-Data_Zone_Standard,_pay_per_token-412991)](https://azure.microsoft.com/en-us/pricing/details/azure-openai/)
[![Foundry IQ tier](https://img.shields.io/badge/Foundry_IQ-free_retrieval_allowance-0078D4)](https://azure.microsoft.com/en-us/pricing/details/search/)
[![Azure AI Search tier](https://img.shields.io/badge/Azure_AI_Search-Free-0078D4)](https://azure.microsoft.com/en-us/pricing/details/search/)
[![Cosmos DB tier](https://img.shields.io/badge/Cosmos_DB-free_tier-0078D4)](https://azure.microsoft.com/en-us/pricing/details/cosmos-db/autoscale-provisioned/)
[![Document Intelligence tier](https://img.shields.io/badge/Document_Intelligence-F0_free-0078D4)](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/)
[![Azure Container Apps tier](https://img.shields.io/badge/Azure_Container_Apps-Consumption,_0--1_replicas-0078D4)](https://azure.microsoft.com/en-us/pricing/details/container-apps/)
[![Azure Monitor tier](https://img.shields.io/badge/Log_Analytics-pay_as_you_go,_daily_cap-0078D4)](https://azure.microsoft.com/en-us/pricing/details/monitor/)

<!-- Row 6 — live hosting. Not deployed yet: the web UI is planned at https://argus.arjunganesh.dev.
     When it is live these become Vercel-live_frontend-000000 and the API's own badge, each
     linking to the running site. -->
[![Vercel live frontend](https://img.shields.io/badge/Vercel_live_frontend-argus.arjunganesh.dev_not_deployed_yet-6B7280?logo=vercel&logoColor=white)](https://vercel.com)
[![Azure live API](https://img.shields.io/badge/Azure_Container_Apps_live_API-not_deployed_yet-6B7280)](https://azure.microsoft.com/en-us/products/container-apps)

---

## The quiet cost of bad KYC

A refugee family in Germany spends 18 months trying to open a bank account. Their documents are legitimate. But an automated KYC system — never designed with them in mind — scores their jurisdiction as high risk and closes the case. No human review. No plain-language explanation. No appeal path.

An NGO doing legitimate microfinance work in Southeast Asia gets de-risked by their correspondent bank. The letter cites "risk appetite." The lending operation, which supports 4,000 families, can no longer move money.

These aren't edge cases. **1.4 billion people remain financially excluded globally** — and compliance systems built to protect institutions are a leading cause. The same technology meant to stop financial crime routinely shuts out the people who most need access.

ARGUS exists to change that equation.

Not just by making KYC faster — but by building compliance infrastructure that is **explainable, accessible, open, and designed from the ground up for the humans most likely to be failed by the systems they depend on.**

---

## What ARGUS does

A single KYC request fans out across **five specialist agents**. The Identity, Screening, Corporate and Transaction agents run in parallel; the Compliance & Risk agent combines their results into one risk report. Risk scores, tiers and compliance gaps are computed by deterministic code. A language model writes the plain-English explanation of the decision. The report keeps an audit trail of which agents ran, which tools they called, and the citations each finding rests on.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/architecture/investigation-flow-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/architecture/investigation-flow-light.svg">
    <img width="100%" src="assets/architecture/investigation-flow-light.svg" alt="One KYC request in five steps: submit; four agents run in parallel with fixed scoring rules; the Compliance and Risk agent weights the dimensions and sets the tier; a language model writes the explanation but cannot change the score; the report goes to a human reviewer."/>
  </picture>
</p>

📹 [Watch the demo](https://youtu.be/yaTNCgCwX4s)

### What works today, and what doesn't

ARGUS is being rebuilt after the hackathon. This table is the honest state of the code as of September 2026.

| Capability | Status |
| --- | --- |
| Orchestrator fan-out and fan-in across five agents | ✅ Works, as one in-process Microsoft Agent Framework workflow inside the API. `GET /api/v1/kyc/stream/{id}` follows each agent's progress as server-sent events. |
| Deterministic risk scoring, tiering and gap analysis | ✅ Works |
| Plain-English decision explanation | ✅ Works with the model chosen by `ARGUS_MODEL_PROVIDER` (Azure OpenAI, OpenAI or GitHub Models); without one, a fixed template, labelled as such |
| **Local data plane** (default): knowledge-base search, entities, ownership, transactions, reports | ✅ Works with no cloud account, on the synthetic data in `data/`. A clone without generated data finds nothing, and says so. |
| **Azure data plane** (`ARGUS_DATA_BACKEND=azure`): Foundry IQ knowledge bases on AI Search, Cosmos DB, Document Intelligence | ⚠️ Built and tested against stand-ins for the Azure SDKs; **not yet run against live services**. That happens with the deployment work. |
| OCR without Azure | ✅ Tesseract reads the synthetic identity documents (PNG and PDF) when it is installed (the `ocr` dependency group and the Tesseract program); without it, documents are reported as unread, labelled `fallback`. ⚠️ The API does not accept documents yet: OCR runs when the Identity agent is called directly. |
| The six demo scenarios below | ⚠️ Their parallel-agent results come from recorded demo profiles ([`utils/demo_profiles.py`](src/argus/utils/demo_profiles.py)), not live calls. The compliance fan-in still runs live. |
| Web UI ([`web/`](web/): Next.js, TypeScript, shadcn/ui) | ✅ Works locally: submit an entity or a demo case, follow each agent live, read the report. Tested end to end with Playwright and axe. Not deployed yet. |

Every agent result says where it came from: `computed`, `fallback` (a service was unavailable and a result that asserts nothing was used instead), or `demo_profile`. The report's audit trace lists them, names any tool that fell back, and says whether a model or the template wrote the explanation.

---

## Recognition

ARGUS was selected as **1 of 3 Hack for Good winners** in the Microsoft Agents League — AI Skills Fest 2026. The submission material (runbooks, narration script, slides, original architecture spec) is preserved unchanged in [`archive/hackathon-2026/`](archive/hackathon-2026/).

---

## How ARGUS works

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/architecture/system-overview-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/architecture/system-overview-light.svg">
    <img width="100%" src="assets/architecture/system-overview-light.svg" alt="The current runtime: the Next.js web UI calls one FastAPI process from the browser, which runs the orchestrator's Agent Framework workflow (four agents in parallel, then compliance) and reads data through one data plane: local synthetic data by default, or Foundry IQ knowledge bases, Cosmos DB and Document Intelligence."/>
  </picture>
</p>

| Agent | Tools | Knowledge source |
| --- | --- | --- |
| 🎯 Orchestrator | Agent Framework workflow: fan-out / fan-in | — |
| 🪪 Identity | customer_lookup, ocr_processor, identity_validator | Entity store, OCR |
| 🔍 Screening | sanctions_checker, adverse_media_scanner, pep_checker | Sanctions and adverse media knowledge bases, entity store |
| 🏢 Corporate Intelligence | ubo_resolver, registry_lookup, jurisdiction_mapper | Entity store (ownership graph) |
| ⚖️ Compliance & Risk | regulations_rag, risk_scorer, gap_analyzer, explain_decision | Regulations knowledge base, language model (explanation only) |
| 💳 Transaction Intelligence | transaction_monitor, pattern_detector, typology_matcher | Entity store (transactions), regulations knowledge base |

Each source is one of four data-plane interfaces with a local and an Azure implementation; see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#data-plane).

---

## Where ARGUS is going

The next version is planned in [`docs/ARGUS-V2-PLAN.md`](docs/ARGUS-V2-PLAN.md).

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/architecture/v2-target-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/architecture/v2-target-light.svg">
    <img width="100%" src="assets/architecture/v2-target-light.svg" alt="The v2 runtime, partly built and not deployed: Next.js on Vercel, one FastAPI container on Azure Container Apps, a Microsoft Agent Framework workflow with Explain Mode and human review, one model-provider setting, Foundry IQ, Fabric IQ and Work IQ, and a data plane with Azure and local implementations."/>
  </picture>
</p>

In short:

- **A focused experiment first.** Can ARGUS produce simpler explanations while preserving evidence, uncertainty, and the need for human review? It will be measured on a fixed evaluation set and written up, including failures.
- **A simpler runtime.** Done: one process on Microsoft Agent Framework instead of six services, one container, and a Next.js UI. Next: deploying them (Azure Container Apps and Vercel).
- **All three Microsoft IQs.** Foundry IQ for cited regulatory knowledge, Fabric IQ for evaluation data and corporate-ownership relationships, and Work IQ for case-handover context.
- **Neutral where it's cheap.** The model provider, the container host, the tools (MCP) and telemetry can be swapped by configuration. The data plane stays Azure, with a local implementation for tests and self-hosting.

Longer-term ideas, not yet scheduled, live in [`docs/roadmap/`](docs/roadmap/): full WCAG 2.1 AA accessibility, a community edition for NGOs, an open knowledge graph, multimodal identity evidence, and adverse-event alerts. Current starting points in the code:

- [`accessibility/`](src/argus/accessibility/) has contrast and ARIA utilities. Every audited palette pair passes the WCAG AA normal-text contrast threshold. The web UI's risk badges use that palette as white-on-colour badges; its stylesheet's text colours are checked against WCAG AA in both themes, and its pages are checked with axe in the end-to-end tests. This is not a full accessibility audit.
- [`agents/compliance/tools/explain_decision.py`](src/argus/agents/compliance/tools/explain_decision.py) has the analyst explanation (wired in) and a plain-language variant (not wired in yet).
- [`community/`](src/argus/community/) holds a design and configuration sketch; it doesn't run yet.

---

## Demo scenarios

| Scenario | Entity | Type | Jurisdiction | Expected |
| --- | --- | --- | --- | --- |
| 🔴 Sanctions Hold | `Cayman Synth Capital` | corporate | KY | CRITICAL — Hold until the sanctions match is confirmed or cleared |
| 🟠 Medium Risk | `Synthetic Holdings B.V.` | corporate | NL | MEDIUM — Enhanced Due Diligence (PEP match) |
| 🟢 Low Risk | `Jane Synthetic` | individual | DE | LOW — Standard onboarding |
| 🔴 Public High Risk | `Wirecard AG` | corporate | DE | HIGH — Enhanced Due Diligence |
| 🟠 Public Medium Risk | `Danske Bank A/S` | corporate | DK | MEDIUM — Elevated monitoring |
| 🟠 Public Medium Risk | `Westpac Banking Corporation` | corporate | AU | MEDIUM — Elevated monitoring |

These use recorded demo profiles for the parallel agents (see the status table above).

### What a report shows

- **Investigation** — each agent's progress as it runs (four in parallel, then compliance), its time and where its result came from
- **Recommendation** — risk tier, score, what set the tier (the score band or a sanctions hold), the sanctions screening status, whether enhanced due diligence is required, the recommendation and the findings behind it
- **Risk dimensions** — weight, score and tier for Identity, Screening, Corporate, Regulatory and Transaction
- **Explanation** — the analyst explanation, and whether a model or the template wrote it
- **Citations** — the knowledge base, source document and article behind each regulatory trigger
- **Recommended actions** — driven by risk indicators and compliance gaps
- **Audit trail** — report and task IDs, each agent's status, where its result came from and which tools fell back, the timeline, and the full report as JSON

---

## Quick start

Runs locally without any cloud account, on the local data plane: synthetic data, searched in memory. The six demo scenarios use their recorded profiles.

Requires [uv](https://docs.astral.sh/uv/). It installs the Python version pinned in `.python-version` (3.14) and the locked dependencies.

```bash
git clone https://github.com/iarjunganesh/argus.git
cd argus
uv sync
cp .env.example .env    # optional: choose a model provider or the Azure backend
```

For a populated local data set, generate the synthetic data once: `uv run python data/synthetic/generate_entities.py`, and the other `generate_*.py` scripts in that folder.

Start ARGUS: the API (which runs every agent in-process) and the web UI, which needs [Node.js](https://nodejs.org/) 24. Install the web UI once with `npm ci --prefix web`. On Windows, `scripts/dev/start_demo.ps1` starts both and `scripts/dev/end_demo.ps1` stops them. Elsewhere, start each in its own terminal:

```bash
ARGUS_CORS_ORIGINS=http://localhost:3000 uv run uvicorn argus.api.main:app --port 8000
npm --prefix web run dev    # then open http://localhost:3000
```

The browser calls the API directly, so `ARGUS_CORS_ORIGINS` must list the web UI's origin. More in [`web/README.md`](web/README.md).

Or run one assessment without either: `uv run python scripts/dev/run_demo_inprocess.py`.

Or run the API in a container (no UI; the local backend with the public demo data only):

```bash
docker build -t argus .
docker run --rm -p 8000:8000 argus
python scripts/ci/smoke_api.py    # one demo assessment against http://127.0.0.1:8000
```

Run the same checks as CI:

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest --cov
uv run python scripts/ci/check_docs.py
uv run python scripts/ci/check_versions.py --check
uv run python scripts/ci/render_assets.py --check
npm --prefix web run lint && npm --prefix web run typecheck && npm --prefix web test
```

To run on Azure instead, [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) deploys the API with its data plane (`infra/main.bicep`), fills it (`infra/populate.py`) and removes it again (`infra/teardown.py`).

---

## Contributing

ARGUS is going through a cleanup before the v2 work starts, so the structure is still moving. Issues are welcome: start with [`CONTRIBUTING.md`](CONTRIBUTING.md). [`AGENTS.md`](AGENTS.md) holds the full rules, commands and definition of done for humans and coding agents alike, and security reports go through [`SECURITY.md`](SECURITY.md). The most useful contributions right now:

1. Accessibility review of the web UI with real assistive technology: axe finds no WCAG 2.2 AA violations, but that is not a full audit (see [`docs/roadmap/accessibility.md`](docs/roadmap/accessibility.md))
2. Translations of explanation output — the people who need plain language most often aren't reading in English

---

## License

Copyright (c) 2026 iarjunganesh.

Licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

---

## Disclaimer

ARGUS is a technology demonstration. It is not a licensed compliance tool and must not be used to make real KYC/AML decisions. Core test data is synthetic, with a small public-source adverse-media corpus for demo variety.
