# ARGUS architecture (current runtime)

This page describes how ARGUS runs **today**, as checked against the code on 2026-09-26. The planned
v2 runtime is described in [ARGUS-V2-PLAN.md](ARGUS-V2-PLAN.md). The original hackathon design spec
is archived in [`archive/hackathon-2026/docs/`](../archive/hackathon-2026/docs/ARGUS_Architecture.md)
and is no longer maintained.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/architecture/system-overview-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="../assets/architecture/system-overview-light.svg">
    <img width="100%" src="../assets/architecture/system-overview-light.svg" alt="The current ARGUS runtime: UI, gateway, orchestrator, five agent services and the Azure data plane, with each service's live or mock status."/>
  </picture>
</p>

The diagram's sources and the one-request walkthrough
([`investigation-flow.svg`](../assets/architecture/investigation-flow.svg)) are indexed in
[`assets/README.md`](../assets/README.md). They are kept in step with this page.

## Processes

A local run is seven processes:

| Process | Entry point | Port | Role |
| --- | --- | --- | --- |
| API gateway | `api/main.py` | 8000 | Accepts KYC requests, runs the orchestrator as a background task, serves reports |
| Identity agent | `agents/identity/agent.py` | 8001 | Customer lookup, OCR, identity validation |
| Screening agent | `agents/screening/agent.py` | 8002 | Sanctions, adverse media, PEP checks |
| Corporate agent | `agents/corporate/agent.py` | 8003 | Ownership (UBO), registry lookup, jurisdiction risk |
| Transaction agent | `agents/transaction/agent.py` | 8004 | Transaction monitoring, patterns, typology matching |
| Compliance agent | `agents/compliance/agent.py` | 8005 | Regulations lookup, risk scoring, gap analysis, explanation |
| UI | `ui/gradio_app.py` | 7860 | Gradio front end that calls the API gateway |

`scripts/start_demo.ps1` starts all seven on Windows and `scripts/end_demo.ps1` stops them.

## Request flow

1. The UI posts to `POST /api/v1/kyc/assess`. The gateway returns a `report_id` immediately and
   runs `agents/orchestrator/agent.py` as a FastAPI background task.
2. **Fan-out.** The orchestrator calls the Identity, Screening, Corporate and Transaction agents in
   parallel. Each call is an HTTP `POST /a2a/invoke` carrying a custom JSON envelope
   (`a2a_version`, `source_agent`, `target_agent`, `task_id`, `payload`). Despite the name, this is
   **not** the A2A protocol specification.
3. **Fan-in.** The orchestrator sends all four results to the Compliance agent, which computes the
   risk score, tier and gaps deterministically and asks a language model for a short explanation.
4. The report is stored in an **in-memory dict** in the gateway. The UI polls
   `GET /api/v1/kyc/status/{id}` and `GET /api/v1/kyc/report/{id}`. Reports are lost when the
   gateway restarts.

**Demo shortcut.** When the entity matches one of the six demo scenarios
(`utils/demo_profiles.py`), the orchestrator skips the four parallel agents and uses the recorded
profile. The compliance fan-in still runs live.

An agent that is unreachable is recorded as `status: error` and the assessment continues without it.

## External services and fallbacks

Every external call is wrapped so that a missing service degrades to mock data instead of failing.
Tool results carry a `source` field that reads `mock` when a fallback ran.

| Service | Used by | Without it |
| --- | --- | --- |
| Azure OpenAI GPT-4o, or GitHub Models (`USE_GITHUB_MODELS=true`) | Compliance explanation | Fixed template text |
| Cosmos DB | Customer lookup, registry, UBO, PEP, transactions | Mock records |
| Azure AI Search | Transaction typology matching | Mock result |
| Azure Document Intelligence | OCR | Mock fields. **Also the path taken in every run today**: `ocr_processor` imports `azure.ai.formrecognizer`, which is not a project dependency. |
| Foundry IQ knowledge bases (regulations, sanctions, adverse media) | `regulations_rag`, `sanctions_checker`, `adverse_media_scanner` | Mock results. **This is the path taken in every run today**: the tools call `AIProjectClient.knowledge_bases.query`, which does not exist in `azure-ai-projects` 1.0.0 or 2.6.1. |

Configuration comes from environment variables loaded from `.env` (see `.env.example`).

## Infrastructure

`infra/main.bicep` provisions a storage account, Key Vault, Azure OpenAI with a `gpt-4o`
deployment, an Azure Machine Learning hub and project, Azure AI Search (**Basic** tier), Cosmos DB
and Document Intelligence (F0). The Search Basic tier is billed while it exists, whether or not ARGUS
is running. `data/synthetic/` generates and uploads the synthetic data; `foundry_iq/` creates and
populates the search indexes.

## Tests

`tests/` runs without any cloud credentials: external clients are mocked or fall back. Run
`uv run pytest --cov` from the repository root. CI (`.github/workflows/ci.yml`) also runs ruff,
mypy, a dependency audit, a secret scan, the documentation checks, and a check that the
diagram variants match their SVG masters and pass WCAG AA contrast.
