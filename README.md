# ARGUS

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/brand/banner-light.svg">
    <img width="900" src="assets/brand/banner-light.svg" alt="ARGUS — Agentic Risk & Governance Unified Screening. Explainable KYC screening, built for the people automated compliance fails."/>
  </picture>
</p>

<p align="center">
  <strong>Rules decide. A language model explains. A person reviews.</strong><br/>
  Open, explainable KYC screening, and a study of whether its explanations keep the facts.
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
     Release opens the latest release (the first is v0.1.0). -->
[![CI](https://github.com/iarjunganesh/argus/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/iarjunganesh/argus/actions/workflows/ci.yml)
[![SonarQube Cloud](https://img.shields.io/sonar/quality_gate/iarjunganesh_argus?server=https%3A%2F%2Fsonarcloud.io&logo=sonarqubecloud&label=SonarQube%20Cloud)](https://sonarcloud.io/summary/new_code?id=iarjunganesh_argus)
[![Codecov](https://codecov.io/gh/iarjunganesh/argus/graph/badge.svg)](https://codecov.io/gh/iarjunganesh/argus)
[![Release](https://img.shields.io/badge/release-latest-2ea44f?logo=github&logoColor=white)](https://github.com/iarjunganesh/argus/releases/latest)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Watch Video](https://img.shields.io/badge/%E2%96%B6_Watch-5--min_demo-FF0000?logo=youtube&logoColor=white)](https://youtu.be/yaTNCgCwX4s)

<details>
<summary>Platform and toolchain badges</summary>

<!-- Row 2 — the Microsoft framework and every Azure service ARGUS uses, and what each does.
     Fixed rules set the score and tier; the model only writes the explanation (no model is the
     default: a labelled template). The Azure services are optional: the local data plane, the
     default, needs none of them. -->
[![Microsoft Agent Framework](https://img.shields.io/badge/Agent_Framework-1.26.0-0078D4)](https://github.com/microsoft/agent-framework)
[![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-explanation_only-412991)](https://azure.microsoft.com/en-us/pricing/details/azure-openai/)
[![Foundry IQ](https://img.shields.io/badge/Foundry_IQ-cited_knowledge_bases-0078D4)](https://azure.microsoft.com/en-us/products/ai-foundry/iq)
[![Azure AI Search](https://img.shields.io/badge/Azure_AI_Search-knowledge_base_indexes-0078D4)](https://azure.microsoft.com/en-us/products/ai-services/ai-search)
[![Cosmos DB](https://img.shields.io/badge/Cosmos_DB-entities_and_reports-0078D4)](https://azure.microsoft.com/en-us/products/cosmos-db)
[![Document Intelligence](https://img.shields.io/badge/Document_Intelligence-document_OCR-0078D4)](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence)
[![Azure Container Apps](https://img.shields.io/badge/Azure_Container_Apps-API_host-0078D4)](https://azure.microsoft.com/en-us/products/container-apps)
[![Azure Monitor](https://img.shields.io/badge/Azure_Monitor-API_logs-0078D4)](https://azure.microsoft.com/en-us/products/monitor)

<!-- Row 3 — frontend (web/), hosted on Vercel Hobby (decision D1). -->
[![Next.js](https://img.shields.io/badge/Next.js-16.4-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.3-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Node.js](https://img.shields.io/badge/Node.js-26-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4.3-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![shadcn/ui](https://img.shields.io/badge/shadcn%2Fui-Radix-000000?logo=shadcnui&logoColor=white)](https://ui.shadcn.com/)
[![Playwright](https://img.shields.io/badge/Playwright-1.65-2EAD33)](https://playwright.dev/)
[![axe](https://img.shields.io/badge/axe-4.14_WCAG_2.2_AA-663399)](https://github.com/dequelabs/axe-core)
[![Vercel Hobby](https://img.shields.io/badge/Vercel-Hobby-000000?logo=vercel&logoColor=white)](https://vercel.com/pricing)

<!-- Row 4 — backend and toolchain. -->
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.163-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.14_contracts-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![uv](https://img.shields.io/badge/uv-locked-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/badge/Ruff-lint%20%2B%20format-D7FF64?logo=ruff&logoColor=111827)](https://docs.astral.sh/ruff/)
[![Mypy](https://img.shields.io/badge/Mypy-type_checked-2A6DB2?logo=python&logoColor=white)](https://mypy-lang.org/)
[![pytest](https://img.shields.io/badge/pytest-9.2-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Docker](https://img.shields.io/badge/Docker-non--root,_digest--pinned-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tesseract](https://img.shields.io/badge/Tesseract-local_OCR-3C8DBC)](https://github.com/tesseract-ocr/tesseract)

<!-- Row 5 — the tier of each Azure service in row 2, as chosen in decision D1 (docs/ARCHITECTURE.md,
     "Hosting"), deployed on 18 November 2026. The Azure data plane runs live only for search and
     reports (see "Known issues" in CHANGELOG.md). Each badge opens the service's pricing page. -->
[![Azure OpenAI tier](https://img.shields.io/badge/Azure_OpenAI-Data_Zone_Standard,_pay_per_token-412991)](https://azure.microsoft.com/en-us/pricing/details/azure-openai/)
[![Foundry IQ tier](https://img.shields.io/badge/Foundry_IQ-free_retrieval_allowance-0078D4)](https://azure.microsoft.com/en-us/pricing/details/search/)
[![Azure AI Search tier](https://img.shields.io/badge/Azure_AI_Search-Free-0078D4)](https://azure.microsoft.com/en-us/pricing/details/search/)
[![Cosmos DB tier](https://img.shields.io/badge/Cosmos_DB-free_tier-0078D4)](https://azure.microsoft.com/en-us/pricing/details/cosmos-db/autoscale-provisioned/)
[![Document Intelligence tier](https://img.shields.io/badge/Document_Intelligence-F0_free-0078D4)](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/)
[![Azure Container Apps tier](https://img.shields.io/badge/Azure_Container_Apps-Consumption,_0--1_replicas-0078D4)](https://azure.microsoft.com/en-us/pricing/details/container-apps/)
[![Azure Monitor tier](https://img.shields.io/badge/Log_Analytics-pay_as_you_go,_daily_cap-0078D4)](https://azure.microsoft.com/en-us/pricing/details/monitor/)

</details>

<!-- Row 6 — live hosting, deployed on 18 November 2026: the web UI on Vercel and the API on Azure
     Container Apps, both running the six synthetic demo cases only. Each badge links to the running
     service (the API's to its health check, which answers {"status":"ok"}). The API scales to
     zero when idle, so the first request waits while it wakes. -->
[![Vercel live frontend](https://img.shields.io/badge/Vercel_live_frontend-argus.arjunganesh.dev-000000?logo=vercel&logoColor=white)](https://argus.arjunganesh.dev)
[![Azure live API](https://img.shields.io/badge/Azure_Container_Apps_live_API-demo_cases_only,_wakes_in_up_to_a_minute-0078D4)](https://argus-api.proudbay-27e26eb7.swedencentral.azurecontainerapps.io/health)

---

ARGUS runs the checks of a bank's know-your-customer (KYC) screening: identity, sanctions and
politically exposed persons, company ownership and transactions. Four agents gather the evidence
and a fifth combines it. Fixed, versioned rules turn it into a risk score, a tier and the
obligations that follow. A language model writes the explanation and nothing else, and every case
waits for a person to decide. Every customer, document and transaction ARGUS screens is
synthetic.

**[Try the live demo](https://argus.arjunganesh.dev)** · **[Watch the 5-minute video](https://youtu.be/yaTNCgCwX4s)** · **[Read the study plan](docs/ARGUS-V2-PLAN.md)**

---

## Why it matters

Screening decides who gets a bank account. When software makes that decision, the analyst who
reviews it, and the customer who later asks why, depend on its explanation. Language models make
such explanations cheap to write, and they write fluently whether or not the text matches the
decision. A model can drop a finding, call a *potential* sanctions match confirmed or cleared,
or leave out that a person still has to decide. A wrong explanation is worse than none: it
misleads the reviewer exactly where care is needed.

The stakes are real. About 1.3 billion adults still have no account
([World Bank, Global Findex 2025](https://www.worldbank.org/en/publication/globalfindex)), and
the Financial Action Task Force, which sets the global anti-money-laundering standards, runs a
[project on its standards' unintended consequences](https://www.fatf-gafi.org/content/fatf-gafi/en/publications/Financialinclusionandnpoissues/Unintended-consequences-project.html),
de-risking and financial exclusion among them. ARGUS began as a Hack for Good project with the
people at that edge in mind: those whose documents or countries fall outside what a screening
system expects.

ARGUS does not claim to fix that. It isolates one thing that has to hold before an automated
decision can be reviewed fairly: **the explanation must say what the decision actually rests
on.** So ARGUS keeps the decision and the explanation apart, and measures what happens between
them.

---

## How ARGUS works

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/architecture/investigation-flow-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/architecture/investigation-flow-light.svg">
    <img width="100%" src="assets/architecture/investigation-flow-light.svg" alt="One KYC request in five steps: submit; four agents run in parallel with fixed scoring rules; the Compliance and Risk agent weights the dimensions and sets the tier; a language model writes the explanation but cannot change the score; the report goes to a human reviewer."/>
  </picture>
</p>

1. **Agents gather the evidence.** The Identity, Screening, Corporate and Transaction agents run
   in parallel in one Microsoft Agent Framework workflow, and the Compliance & Risk agent combines
   their results.
2. **Fixed rules decide.** Every result becomes typed findings, and one versioned policy
   (`argus-risk-v1`) computes the dimension scores, the weighted score, the tier and the
   obligations. A potential sanctions match holds the case at CRITICAL whatever the score.
3. **A language model explains, and only explains.** It receives the decision and writes three to
   five sentences for the analyst. It cannot change a score, a tier or a finding. Without a
   model, a fixed template writes the explanation, and the report says so.
4. **A person decides.** Every report is pending human review. Every result says how it was
   produced (`computed`, `fallback` when a service was unavailable, or `demo_profile`), every
   finding carries its uncertainty and evidence, and every regulation cited names its source
   document and article.

---

## See it

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/screenshots/case-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/screenshots/case-light.png">
    <img width="100%" src="assets/screenshots/case-light.png" alt="The ARGUS report for Cayman Synth Capital, a synthetic company, beside the queue of six demo cases: risk tier CRITICAL, risk score 76 of 100, the tier set by a sanctions hold, enhanced due diligence required, and a notice not to onboard or process transactions until a compliance officer confirms or clears the potential sanctions match."/>
  </picture>
</p>

<p align="center"><sub>Cayman Synth Capital, a synthetic company with a potential sanctions match: the tier is held at CRITICAL, and nothing moves until a person confirms or clears the match.</sub></p>

The web UI reads a report as an analyst's case file:

- **Case header**: the tier, the score, what set the tier (the score band or a sanctions hold),
  the sanctions status, whether enhanced due diligence is required, the recommendation and the
  review's state.
- **Potential sanctions match**: the listing beside the customer it may concern, to confirm,
  clear or escalate.
- **Why this score**: each dimension's score times its weight, and behind it the findings with
  their uncertainty, source and evidence records.
- **Explanation**: the analyst explanation, and whether a model or the template wrote it.
- **Review**: a simulated review kept in the browser and sent nowhere. The analyst decides with a
  reason, and a HIGH or CRITICAL decision waits for an approver's sign-off.
- **Audit trail**: which agents ran, how each result was produced, which tools fell back, and the
  full report as JSON.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/screenshots/score-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/screenshots/score-light.png">
    <img width="80%" src="assets/screenshots/score-light.png" alt="The same report further down. Why this score: identity 30 times 20 percent is 6, screening 100 times 30 percent is 30, corporate and ownership 40 times 15 percent is 6, regulatory 100 times 25 percent is 25, transaction 90 times 10 percent is 9, total 76 of 100; the sanctions hold, not the score band, sets the tier. Review: awaiting the analyst. Explanation, written from a template because no language model answered: the case is held at CRITICAL because screening found a potential sanctions match, and a compliance officer must confirm or clear it before any onboarding decision."/>
  </picture>
</p>

<p align="center"><sub>Rules decide, the explanation follows. The dimension scores add up to 76, the sanctions hold sets the tier, and the explanation says who wrote it: in this local run no model was configured, so the fixed template did.</sub></p>

### Demo scenarios

The six demo cases, riskiest first. The live site offers only these.

| Entity | Type | Jurisdiction | Score and tier | Recommendation |
| --- | --- | --- | --- | --- |
| 🔴 `Cayman Synth Capital` | corporate | KY | 76.0 CRITICAL | Hold until the sanctions match is confirmed or cleared |
| 🔴 `Synthetic Payments AG` | corporate | DE | 56.5 HIGH | Enhanced due diligence (PEP match, offshore owners, structuring) |
| 🟠 `Synthetic Holdings B.V.` | corporate | NL | 44.0 MEDIUM | Enhanced due diligence (PEP match) |
| 🟠 `Synthetic Nordic Bank A/S` | corporate | DK | 36.0 MEDIUM | Enhanced due diligence (PEP match) |
| 🟢 `Synthetic Pacific Banking Corporation` | corporate | AU | 18.2 LOW | Standard onboarding, despite adverse media and a structuring flag |
| 🟢 `Jane Synthetic` | individual | DE | 3.0 LOW | Standard onboarding |

Every entity is invented. The four parallel agents' results come from recorded profiles; the
scoring, the decision and the explanation run live. A test
([`tests/test_demo_scenarios.py`](tests/test_demo_scenarios.py)) fails if any scenario's score,
tier or recommended actions change.

---

## Where ARGUS is heading

### Now: does the explanation keep the facts?

The next piece of work is a small, planned study, with every procedure written down before any
model output is read ([the protocol](docs/research/study-protocol.md)). It asks three questions:

1. When a model explains a decision that rules made, does it keep the findings, the evidence,
   the uncertainty and the need for human review?
2. Does that change when it receives minimised typed findings, without the entity's name,
   instead of the raw case? Which case strings reach the model either way?
3. What happens when a case field carries an injected instruction, or one workflow step's result
   is missing?

| | Design |
| --- | --- |
| **Cases** | 24 synthetic cases in eight strata, from clear cases to many findings, with PEP matches, potential sanctions matches, partial evidence, missing assessments and conflicting findings. 8 tune the prompts; the outputs of the other 16 are not read until the prompts are frozen. |
| **Arms** | A: today's analyst prompt with the raw case. B: the same instructions with minimised typed findings. C: the fixed template, no model. |
| **Reference** | Written for each case before any output is read: the required facts, the evidence, the uncertainty, the review status and the permitted next steps. |
| **Stress tests** | The same injected instruction in two fields of six cases, and two missing-step variants of six cases, with the expected behaviour written down first. |
| **Model** | Azure OpenAI `gpt-5.4-mini`, version `2026-03-17`, pinned, with five repeats per item to measure variability. |
| **Spend** | US$20 for the whole study, enforced in code: each attempt reserves its worst-case cost before it is sent, and the run stops before an attempt that would pass the ceiling. |
| **Reporting** | Every request and response saved. Each result given with its numerator and denominator, by stratum, with failures quoted in full and null results reported as null. |

| Step | Status |
| --- | --- |
| Typed findings and the decision record every arm is checked against | ✅ Done (16 November 2026) |
| The protocol, the model and the budget | ✅ Model and budget approved on 22 November 2026; protocol frozen on 25 November 2026 |
| Week 1: a baseline of today's explanation (six demo scenarios, arm A, five repeats) | 🔧 Command and spending stop built; the first model run is next |
| Week 2: the case set, the per-case references and the minimised input | Planned |
| Week 3: arms A, B and C on every case | Planned |
| Week 4: the injection and missing-step pairs | Planned |
| Week 5: one targeted improvement, rerun, with its regressions reported | Planned |
| Week 6: the technical report and a summary article, with the run files to reproduce them | Planned |

The study measures faithfulness to ARGUS's own rules on synthetic cases. It will not show that
ARGUS improves real screening, and it does not try to.

### After the study

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/architecture/v2-target-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/architecture/v2-target-light.svg">
    <img width="100%" src="assets/architecture/v2-target-light.svg" alt="The v2 runtime, partly built, with the built part deployed: Next.js on Vercel, one FastAPI container on Azure Container Apps, a Microsoft Agent Framework workflow with the planned explanation study and human review, one model-provider setting, Foundry IQ, the later Fabric IQ and Work IQ integrations, and a data plane with Azure and local implementations."/>
  </picture>
</p>

The target runtime: solid outlines are built, dashed ones are planned.

- **Plain language for the person screened.** Once faithfulness is measured, the follow-up
  question is whether the wording can be made simpler without losing it. A plain-language
  variant of the explanation is in the code, not yet wired in.
- **All three Microsoft IQs.** Foundry IQ already serves the regulations. Fabric IQ, for
  evaluation data and ownership relationships, and Work IQ, for case-handover context, come after
  the first write-up.
- **Neutral where it's cheap.** The model provider already changes with one setting; the goal is
  the same for the container host, the tools (MCP) and telemetry. The data plane stays Azure, with
  a local implementation for tests and self-hosting.
- **Longer term**, in [`docs/roadmap/`](docs/roadmap/): an accessibility review with assistive
  technology, a community edition for NGOs, durable execution, an open knowledge graph,
  multimodal identity evidence and adverse-event reports.

---

## What works today, and what doesn't

ARGUS was rebuilt after the hackathon. This table describes the current code; the dated checks
and the next step are in [`HANDOFF.md`](HANDOFF.md).

| Capability | Status |
| --- | --- |
| Orchestrator fan-out and fan-in across five agents | ✅ Works, as one in-process Microsoft Agent Framework workflow inside the API. `GET /api/v1/kyc/stream/{id}` follows each agent's progress as server-sent events. |
| Deterministic risk scoring, tiering and gap analysis | ✅ Works |
| Plain-English decision explanation | ✅ Works. On the deployment, Azure OpenAI `gpt-5.4-mini` writes it; elsewhere, the model chosen by `ARGUS_MODEL_PROVIDER` (Azure OpenAI, OpenAI or GitHub Models). Without one, a fixed template writes it, labelled as such. |
| **Local data plane** (default): knowledge-base search, entities, ownership, transactions, reports | ✅ Works with no cloud account, on the synthetic data in `data/`. A clone without generated data finds nothing, and says so. |
| **Azure data plane** (`ARGUS_DATA_BACKEND=azure`): Foundry IQ knowledge bases on AI Search, Cosmos DB, Document Intelligence | ⚠️ The deployment runs the knowledge-base search (regulations) and the report store live. The entity store, the sanctions and adverse-media searches and Document Intelligence have **not yet run live**: the public demo takes the four parallel agents' results from recorded profiles, and the API takes no documents. |
| OCR without Azure | ✅ Tesseract reads the synthetic identity documents (PNG and PDF) when it is installed (the `ocr` dependency group and the Tesseract program); without it, documents are reported as unread, labelled `fallback`. ⚠️ The API does not accept documents yet: OCR runs when the Identity agent is called directly. |
| The six demo scenarios | ⚠️ Their parallel-agent results come from recorded demo profiles ([`utils/demo_profiles.py`](src/argus/utils/demo_profiles.py)), not live calls. The compliance fan-in still runs live. |
| Web UI ([`web/`](web/): Next.js, TypeScript, shadcn/ui) | ✅ Works locally (submit an entity or a demo case, follow each agent live, read the report as a case file) and at [argus.arjunganesh.dev](https://argus.arjunganesh.dev), which offers the six demo cases only. Tested end to end with Playwright and axe. |

---

## Architecture

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
| 💳 Transaction Intelligence | transaction_monitor, pattern_detector, typology_matcher | Entity store (transactions), regulations knowledge base |
| ⚖️ Compliance & Risk | regulations_rag, risk_scorer, gap_analyzer, explain_decision | Regulations knowledge base, language model (explanation only) |

Each source is one of four data-plane interfaces with a local and an Azure implementation. The
JSON report carries the typed findings, an evidence index and a decision record with the policy
version; see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#typed-findings-and-decision-record).

---

## Quick start

Runs locally without any cloud account, on the local data plane: synthetic data, searched in
memory. The six demo scenarios use their recorded profiles.

Requires [uv](https://docs.astral.sh/uv/). It installs the Python version pinned in
`.python-version` (3.14) and the locked dependencies.

```bash
git clone https://github.com/iarjunganesh/argus.git
cd argus
uv sync
cp .env.example .env    # optional: choose a model provider or the Azure backend
```

For a populated local data set, generate the synthetic data once: `uv run python data/synthetic/generate_entities.py`, and the other `generate_*.py` scripts in that folder.

Start ARGUS: the API (which runs every agent in-process) and the web UI, which needs [Node.js](https://nodejs.org/) 26. Install the web UI once with `npm ci --prefix web`. On Windows, `scripts/dev/start_demo.ps1` starts both and `scripts/dev/end_demo.ps1` stops them. Elsewhere, start each in its own terminal:

```bash
ARGUS_CORS_ORIGINS=http://localhost:3000 uv run uvicorn argus.api.main:app --port 8000
npm --prefix web run dev    # then open http://localhost:3000
```

The browser calls the API directly, so `ARGUS_CORS_ORIGINS` must list the web UI's origin. More in [`web/README.md`](web/README.md).

Or run one assessment without either: `uv run python scripts/dev/run_demo_inprocess.py`.

Or run the API in a container (no UI; the local backend holds no data in the image, so the six demo scenarios run from their recorded profiles):

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

## Recognition

ARGUS was selected as **1 of 3 Hack for Good winners** in the Microsoft Agents League — AI Skills
Fest 2026. The submission material (runbooks, narration script, slides, original architecture
spec) is preserved unchanged in [`archive/hackathon-2026/`](archive/hackathon-2026/).

---

## Contributing

The next work is the study above; [`HANDOFF.md`](HANDOFF.md) has the order. Issues are welcome:
start with [`CONTRIBUTING.md`](CONTRIBUTING.md). [`AGENTS.md`](AGENTS.md) holds the full rules,
commands and definition of done for humans and coding agents alike, and security reports go
through [`SECURITY.md`](SECURITY.md). The most useful contributions right now:

1. **Critique of the study design.** The [protocol](docs/research/study-protocol.md) is open: a
   flaw found before the runs is worth far more than one found after.
2. **Accessibility review of the web UI with real assistive technology.** axe finds no WCAG 2.2
   AA violations, but that is not a full audit (see
   [`docs/roadmap/accessibility.md`](docs/roadmap/accessibility.md)).
3. **Translations of explanation output.** The people who most need plain language are often not
   reading in English.

---

## Citing ARGUS

Every GitHub release is archived on Zenodo. To cite ARGUS, use its concept DOI, which always
resolves to the latest version: [10.5281/zenodo.24292413](https://doi.org/10.5281/zenodo.24292413). Version 0.1.0 is
[10.5281/zenodo.24292414](https://doi.org/10.5281/zenodo.24292414). GitHub's "Cite this repository" button reads
[`CITATION.cff`](CITATION.cff).

---

## License

Copyright (c) 2026 iarjunganesh.

Licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

---

## Disclaimer

ARGUS is a technology demonstration. It is not a licensed compliance tool and must not be used to make real KYC/AML decisions. All test and demo data is synthetic.
