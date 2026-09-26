# ARGUS architecture (current runtime)

This page describes how ARGUS runs **today**, as checked against the code on 2026-09-27. The planned
v2 runtime is described in [ARGUS-V2-PLAN.md](ARGUS-V2-PLAN.md). The original hackathon design spec
is archived in [`archive/hackathon-2026/docs/`](../archive/hackathon-2026/docs/ARGUS_Architecture.md)
and is no longer maintained.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/architecture/system-overview-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="../assets/architecture/system-overview-light.svg">
    <img width="100%" src="../assets/architecture/system-overview-light.svg" alt="The current ARGUS runtime: UI, gateway, orchestrator and five agent services, reading data through one data plane with an Azure and a local implementation."/>
  </picture>
</p>

The diagram's sources and the one-request walkthrough
([`investigation-flow.svg`](../assets/architecture/investigation-flow.svg)) are indexed in
[`assets/README.md`](../assets/README.md). They are kept in step with this page.

## Processes

A local run is seven processes:

| Process | Entry point | Port | Role |
| --- | --- | --- | --- |
| API gateway | `src/argus/api/main.py` | 8000 | Accepts KYC requests, runs the orchestrator as a background task, serves reports |
| Identity agent | `src/argus/agents/identity/agent.py` | 8001 | Customer lookup, OCR, identity validation |
| Screening agent | `src/argus/agents/screening/agent.py` | 8002 | Sanctions, adverse media, PEP checks |
| Corporate agent | `src/argus/agents/corporate/agent.py` | 8003 | Ownership (UBO), registry lookup, jurisdiction risk |
| Transaction agent | `src/argus/agents/transaction/agent.py` | 8004 | Transaction monitoring, patterns, typology matching |
| Compliance agent | `src/argus/agents/compliance/agent.py` | 8005 | Regulations lookup, risk scoring, gap analysis, explanation |
| UI | `src/argus/ui/gradio_app.py` | 7860 | Gradio front end that calls the API gateway |

`scripts/dev/start_demo.ps1` starts all seven on Windows and `scripts/dev/end_demo.ps1` stops them.

## Request flow

1. The UI posts to `POST /api/v1/kyc/assess`. The gateway returns a `report_id` immediately and
   runs `src/argus/agents/orchestrator/agent.py` as a FastAPI background task.
2. **Fan-out.** The orchestrator calls the Identity, Screening, Corporate and Transaction agents in
   parallel. Each call is an HTTP `POST /a2a/invoke` carrying a custom JSON envelope
   (`a2a_version`, `source_agent`, `target_agent`, `task_id`, `payload`). Despite the name, this is
   **not** the A2A protocol specification.
3. **Fan-in.** The orchestrator sends all four results to the Compliance agent, which computes the
   risk score, tier and gaps deterministically and asks a language model for a short explanation.
4. The gateway stores the report through the data plane's `ReportStore`: in memory with the local
   backend (lost when the gateway restarts), in Cosmos DB (`kyc_reports`) with the Azure backend.
   The UI polls `GET /api/v1/kyc/status/{id}` and `GET /api/v1/kyc/report/{id}`.

**Demo shortcut.** When the entity matches one of the six demo scenarios
(`src/argus/utils/demo_profiles.py`), the orchestrator skips the four parallel agents and uses the recorded
profile. The compliance fan-in still runs live.

An agent that is unreachable is recorded as `status: error` and the assessment continues without it.

## Provenance: where each result came from

Every agent response carries a `source`, and the report's `audit_trace` collects them in
`agent_sources`:

| `source` | Meaning |
| --- | --- |
| `computed` | Every tool the agent ran answered from the configured data plane |
| `fallback` | At least one tool's service was unavailable; that tool returned a result that asserts nothing (not found, no hits, no fields read). `audit_trace.fallbacks` names the tools. |
| `demo_profile` | A recorded demo scenario, not computed |
| `unavailable` | The agent itself could not be reached |

The report's `explanation_source` says whether a language model wrote the explanation (`model`) or
the fixed template did (`fallback`). `audit_trace.retrieval_queries` counts only knowledge-base
searches that answered, and `audit_trace.data_backend` names the data plane in use.

## Data plane

Agents never call Azure directly. Each tool reads through one of four interfaces in
[`src/argus/data_plane/`](../src/argus/data_plane/) (decision D6), and `ARGUS_DATA_BACKEND` picks
the implementation set:

| Interface | Used by | `local` (default) | `azure` |
| --- | --- | --- | --- |
| `Retriever` | `regulations_rag`, `sanctions_checker`, `adverse_media_scanner`, `typology_matcher` | Keyword search, weighted by word rarity, over the same documents the Azure indexes hold | Azure AI Search, semantic ranker |
| `EntityStore` | `customer_lookup`, `registry_lookup`, `ubo_resolver`, `pep_checker`, `transaction_monitor` | `data/synthetic/*.jsonl` | Cosmos DB |
| `ReportStore` | The API gateway | In memory | Cosmos DB `kyc_reports` |
| `OCR` | `ocr_processor` | None yet: documents are reported as unread (`fallback`) | Document Intelligence, prebuilt ID model |

The regulations corpus and the builders that turn synthetic records into search documents live in
`src/argus/data_plane/corpus.py`, and `infra/foundry_iq/` uploads exactly those documents, so both
backends answer from the same content. A screening hit also needs every word of the entity's name,
or of one alias, to appear in the retrieved passage.

With the local backend, a fresh clone without generated data finds nothing and says so; run the
generators in `data/synthetic/` for a populated local data set. The Azure implementations are
covered by tests against stand-ins for the Azure SDKs; they have not yet been run against live
services (that happens with the deployment work).

The language model is chosen separately by `ARGUS_MODEL_PROVIDER` (`none` by default, or
`azure-openai`, `openai`, `github-models`) in `src/argus/models.py`. It only writes the
explanation. Settings are read from environment variables, or from `.env` (see `.env.example`).

## Hosting (decision D1, recorded 2026-09-27; not deployed yet)

The planned deployment keeps the idle cost near zero, within a $500 sponsorship that ends
2027-06-30 and a $15 monthly budget alert. Region: Sweden Central.

| Part | Choice | Cost when idle |
| --- | --- | --- |
| API | Azure Container Apps, consumption plan, 0 to 1 replicas | $0 (within the monthly free grant) |
| Container image | GitHub Container Registry | $0 |
| Web UI | Vercel, Hobby plan | $0 |
| Search | Azure AI Search **Free** (50 MB, 3 indexes; agentic retrieval and semantic ranker are available on Free in this region) | $0 |
| Entities and reports | Cosmos DB free tier | $0 |
| OCR | Document Intelligence F0 | $0 |
| Model | Azure OpenAI `gpt-5.4-mini` and `text-embedding-3-small`, EU data zone, pay per call | $0 |
| Logs | Log Analytics with a daily cap | About $0 |

Search moves to Basic ($0.101 an hour, about $74 a month at list price) only when the data outgrows
50 MB or keyless access is needed; Free can't be converted in place, so that means a new service
and a re-index. The idle cost is an estimate until the exit gate observes a full idle day.

## Infrastructure

`infra/main.bicep` still describes the hackathon deployment: a storage account, Key Vault, Azure
OpenAI with a `gpt-4o` deployment, an Azure Machine Learning hub and project, Azure AI Search
(**Basic** tier), Cosmos DB and Document Intelligence (F0). It does not match D1 above (its Search
tier is billed while it exists) and is replaced in the deployment work; nothing is deployed from it
today. `data/synthetic/` generates and uploads the synthetic data; `infra/foundry_iq/` creates and
populates the search indexes.

## Tests

`tests/` runs without any cloud credentials: the local data plane reads the small data set in
`tests/fixtures/data/`, and Azure SDKs are replaced by stand-ins. Run
`uv run pytest --cov` from the repository root. CI (`.github/workflows/ci.yml`) also runs ruff,
mypy, a dependency audit, a secret scan, the documentation checks, and a check that the
diagram variants match their SVG masters and pass WCAG AA contrast.
