# ARGUS architecture (current runtime)

This page describes how ARGUS runs **today**, as checked against the code on 2026-09-28. The planned
v2 runtime is described in [ARGUS-V2-PLAN.md](ARGUS-V2-PLAN.md). The original hackathon design spec
is archived in [`archive/hackathon-2026/docs/`](../archive/hackathon-2026/docs/ARGUS_Architecture.md)
and is no longer maintained.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/architecture/system-overview-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="../assets/architecture/system-overview-light.svg">
    <img width="100%" src="../assets/architecture/system-overview-light.svg" alt="The current ARGUS runtime: the Next.js web UI calls one API process from the browser, which runs the orchestrator's Agent Framework workflow (four agents in parallel, then compliance) and reads data through one data plane with an Azure and a local implementation."/>
  </picture>
</p>

The diagram's sources and the one-request walkthrough
([`investigation-flow.svg`](../assets/architecture/investigation-flow.svg)) are indexed in
[`assets/README.md`](../assets/README.md). They are kept in step with this page.

## Processes

A local run is two processes:

| Process | Entry point | Port | Role |
| --- | --- | --- | --- |
| API | `src/argus/api/main.py` | 8000 | Accepts KYC requests, runs each assessment's workflow in this process, streams its progress, serves reports |
| Web UI | `web/` (Next.js) | 3000 | The browser front end: submits assessments, follows their progress stream, shows the report |

The five agents are not services: each is a module with one `assess(request, task_id)` function,
run as a step of the orchestrator's workflow inside the API process.

| Agent | Module | Role |
| --- | --- | --- |
| Identity | `src/argus/agents/identity/agent.py` | Customer lookup, OCR, identity validation |
| Screening | `src/argus/agents/screening/agent.py` | Sanctions, adverse media, PEP checks |
| Corporate | `src/argus/agents/corporate/agent.py` | Ownership (UBO), registry lookup, jurisdiction risk |
| Transaction | `src/argus/agents/transaction/agent.py` | Transaction monitoring, patterns, typology matching |
| Compliance | `src/argus/agents/compliance/agent.py` | Regulations lookup, risk scoring, gap analysis, explanation |

`scripts/dev/start_demo.ps1` starts both on Windows and `scripts/dev/end_demo.ps1` stops them.
`uv run python scripts/dev/run_demo_inprocess.py` runs one assessment without either.

## Web UI

`web/` is a Next.js (App Router) site in TypeScript with shadcn/ui components. It has no server
logic of its own: the browser calls the API at `NEXT_PUBLIC_API_URL` (set at build time), so the
API must list the site's origin in `ARGUS_CORS_ORIGINS` (empty by default, which blocks every
browser origin). The start page submits an assessment; `/assessments/{id}` opens the progress
stream with `EventSource`, draws the workflow's fan-out and fan-in with each agent's state, time
and `source`, and when the stream's `status` event arrives fetches the report. If the stream
closes at its time limit while the assessment is still running, the browser reconnects with
`Last-Event-ID` and resumes. Its colours are the audited palette in
`src/argus/accessibility/wcag.py`, checked for WCAG AA in both themes by
`scripts/ci/render_assets.py --check`. See [`web/README.md`](../web/README.md).

## Container image

The root `Dockerfile` builds the API alone (the web UI is not in it): a multi-stage `uv` build
on the Python image of the `.python-version` minor, installing the runtime dependencies only (no
dependency groups: no dev tools, data generators or Tesseract), from wheels only
(`--no-build`, so no package's build script runs). It runs as a non-root user
(uid 10001), listens on port 8000, and its `HEALTHCHECK` calls `/health`. Both base images are
pinned by tag and digest, checked by `scripts/ci/check_versions.py` and moved by the post-release
refresh. `.dockerignore` is an allow-list, so `.env` and other local files never reach the build.

With no settings the container runs on the local backend, which in the image has only the public
demo data (`data/public/`): synthetic data is generated, never baked in, so entity lookups find
nothing and say so, and the six demo scenarios work. Deployments set `ARGUS_DATA_BACKEND=azure`.
CI builds the image and runs one demo assessment through it (`scripts/ci/smoke_api.py`), then
waits for the health check to pass.

## Request flow

1. The UI posts to `POST /api/v1/kyc/assess`. The API returns a `report_id` immediately and runs
   the assessment as a FastAPI background task.
2. The orchestrator (`src/argus/agents/orchestrator/agent.py`) runs the assessment as one
   **Microsoft Agent Framework workflow** (`agent-framework-core`, pinned to an exact version),
   built with `WorkflowBuilder`: a dispatch step, then a **fan-out** to the Identity, Screening,
   Corporate and Transaction agents, which run concurrently, then a **fan-in** to the Compliance
   agent, which receives all four results, computes the risk score, tier and gaps
   deterministically and asks a language model for a short explanation. No model takes part in
   the workflow's routing; it is a fixed graph.
3. Each agent's start and finish (with its `source` and any `fallbacks`) is recorded through the
   data plane's `ReportStore` as it happens. `GET /api/v1/kyc/stream/{id}` sends these as
   server-sent events (`agent_started`, `agent_completed`, then one `status` event), replaying
   what was recorded before the client connected; a client that reconnects with `Last-Event-ID`
   resumes after the last event it received.
4. The API stores the report through the `ReportStore`: in memory with the local backend (lost
   when the API restarts), in Cosmos DB (`kyc_reports`) with the Azure backend. The UI follows
   the stream, then fetches `GET /api/v1/kyc/report/{id}`; it asks
   `GET /api/v1/kyc/status/{id}` only when the stream is refused, to tell an unknown ID from an
   API it cannot reach. `GET /health` answers while the process is up.

The API's shape is pinned by `tests/test_api_contract.py`: the reviewed OpenAPI document in
`tests/fixtures/openapi.json`, and the fields of the report and of the progress events.

**Demo shortcut.** When the entity matches one of the six demo scenarios
(`src/argus/utils/demo_profiles.py`), the four parallel steps use the recorded profile instead of
running their agents. The compliance fan-in still runs live.

An agent that raises is recorded as `status: error`, `source: unavailable`, and the assessment
continues without it. There is no A2A protocol: if a process boundary is ever needed, the plan is
the real protocol through Agent Framework's A2A support, not a custom envelope.

## Risk scoring

All in [`src/argus/agents/compliance/`](../src/argus/agents/compliance/); no model is involved.
Each agent's own rules are drawn in
[`investigation-flow.svg`](../assets/architecture/investigation-flow.svg).

**Weighted score (0–100).** Screening 30%, Regulatory 25%, Identity 20%, Corporate 15%,
Transaction 10%. The Regulatory dimension is an estimate from other agents' flags, not from
retrieved regulations: PEP 45, adverse media 35, 15 per ownership risk flag, capped at 100. When
adverse media is the only screening hit and the screening score is at least 70, 12 points are
added; today only recorded demo profiles reach that screening score, because live screening
scores adverse media alone at 15.

**Tier.** LOW 0–34, MEDIUM 35–54, HIGH 55–74, CRITICAL 75 and above, with one exception:

- **A potential sanctions match holds the case at CRITICAL, whatever the score**
  (`risk_summary.tier_basis: sanctions_match`). Sanctions are not a risk to be weighed: FATF
  Recommendation 6 requires funds of listed persons to be frozen without delay, and the Wolfsberg
  Group's sanctions-screening guidance treats each match as an alert that a person confirms or
  clears. ARGUS finds a match when the entity's full name, or one alias, appears in a retrieved
  listing, so it is always *potential*. The report recommends a hold until a compliance officer
  confirms or clears it, and says what to do if it is confirmed.
- Otherwise `tier_basis` is `score`.

**Sanctions screening status** (`risk_summary.sanctions_screening`): `potential_match`,
`no_match`, or `not_run` when the screening agent failed or its sanctions search fell back. A
`not_run` case is reported as incomplete whatever its tier, because no match found is not the same
as no screening done.

**A PEP match requires enhanced due diligence, whatever the tier** (`risk_summary.edd_required`).
PEP status calls for measures, not a higher risk tier: the EU AML Regulation (Article 42) and the
UK Money Laundering Regulations (regulation 35) apply senior management approval, source of wealth
and funds, and enhanced ongoing monitoring to every PEP; FATF Recommendation 12 applies them to
every foreign PEP and to domestic PEPs in higher-risk relationships; and the FCA's guidance says
no single factor should automatically make a customer higher risk. So the tier stays as scored, the
recommendation names the three measures (unless a sanctions hold, an incomplete screening or a
CRITICAL tier says more), and the actions list them. ARGUS does not yet tell foreign from
domestic PEPs, so it applies the all-PEP rule.

**What the report does not claim.** It carries no confidence figure: nothing in ARGUS computes one.

Sources: [FATF Recommendations](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Fatf-recommendations.html)
(R.6, R.12 and the glossary's "without delay");
[Wolfsberg Guidance on Sanctions Screening](https://wolfsberg-group.org/resources/168/53);
[EU AML Regulation, Article 42](https://eur-lex.europa.eu/eli/reg/2024/1624/oj/eng);
[FCA FG25/3 on PEPs](https://www.fca.org.uk/publication/finalised-guidance/fg25-3.pdf).

## Provenance: where each result came from

Every agent response carries a `source`, and the report's `audit_trace` collects them in
`agent_sources`:

| `source` | Meaning |
| --- | --- |
| `computed` | Every tool the agent ran answered from the configured data plane |
| `fallback` | At least one tool's service was unavailable; that tool returned a result that asserts nothing (not found, no hits, no fields read). `audit_trace.fallbacks` names the tools. |
| `demo_profile` | A recorded demo scenario, not computed |
| `unavailable` | The agent itself failed, so there is no result |

The report's `explanation_source` says whether a language model wrote the explanation (`model`) or
the fixed template did (`fallback`). `audit_trace.retrieval_queries` counts only knowledge-base
searches that answered, and `audit_trace.data_backend` names the data plane in use.

Regulatory triggers are retrieved passages only: when the regulations search is unavailable or
finds nothing relevant, the report lists none. A typology search that falls back still names the
patterns ARGUS's own rules detected (`source: rules`, no document cited), and the transaction
agent is marked `fallback`.

The repository's `.env` is loaded by the data plane, the model factory and the API, whichever is
imported first, so a setting there takes effect however ARGUS is started.

## Data plane

Agents never call Azure directly. Each tool reads through one of four interfaces in
[`src/argus/data_plane/`](../src/argus/data_plane/) (decision D6), and `ARGUS_DATA_BACKEND` picks
the implementation set:

| Interface | Used by | `local` (default) | `azure` |
| --- | --- | --- | --- |
| `Retriever` | `regulations_rag`, `sanctions_checker`, `adverse_media_scanner`, `typology_matcher` | Keyword search, weighted by word rarity, over the same documents the Azure indexes hold | Foundry IQ knowledge bases: the retrieve action on Azure AI Search (stable API 2026-04-01; semantic intent, minimal extractive retrieval, no model), ranked by the semantic reranker |
| `EntityStore` | `customer_lookup`, `registry_lookup`, `ubo_resolver`, `pep_checker`, `transaction_monitor` | `data/synthetic/*.jsonl` | Cosmos DB |
| `ReportStore` | The API (reports, status and progress events) | In memory | Cosmos DB `kyc_reports` |
| `OCR` | `ocr_processor` | Tesseract, reading the `Label: value` lines of the synthetic documents (PNG, or PDF pages rendered at 300 dpi), when the `ocr` group and the Tesseract program are installed; otherwise documents are unread (`fallback`) | Document Intelligence, prebuilt ID model |

The API does not accept identity documents yet: `KYCRequest` has no documents field, so OCR runs
only when the Identity agent's `assess` is called directly with `documents` (as the tests do).

The regulations corpus and the builders that turn synthetic records into search documents live in
`src/argus/data_plane/corpus.py`, and `infra/foundry_iq/` uploads exactly those documents, so both
backends answer from the same content. `infra/foundry_iq/create_knowledge_bases.py` creates, for each
of the three knowledge bases, its index, a knowledge source over that index, and the knowledge base. A screening hit also needs every word of the entity's name,
or of one alias, to appear in the retrieved passage.

With the local backend, a fresh clone without generated data finds nothing and says so; run the
generators in `data/synthetic/` for a populated local data set. The Azure implementations are
covered by tests against stand-ins for the Azure SDKs; they have not yet been run against live
services (that happens with the deployment work).

The language model is chosen separately by `ARGUS_MODEL_PROVIDER` (`none` by default, or
`azure-openai`, `openai`, `github-models`) in `src/argus/models.py`. It only writes the
explanation. Reasoning models (the GPT-5 family, including the planned `gpt-5.4-mini`, and the
o-series) reject `max_tokens` and `temperature`, so they are called with `max_completion_tokens`
only; `ARGUS_MODEL_REASONING` (`auto` from the model name, or `true`/`false`) says which kind the
model is. Settings are read from environment variables, or from `.env` (see `.env.example`).

Cosmos DB, Document Intelligence and Azure OpenAI take a key when one is set and otherwise sign
in with Microsoft Entra ID through one shared credential (`argus.config.get_azure_credential`):
the managed identity when deployed, the developer's `az login` locally. AI Search always takes a
key, because its Free tier has no keyless access.

## Hosting (decision D1, recorded 2026-09-27; not deployed yet)

The planned deployment keeps the idle cost near zero, within a $500 sponsorship that ends
2027-06-30 and a $15 monthly budget alert. Region: Sweden Central.

| Part | Choice | Cost when idle |
| --- | --- | --- |
| API | Azure Container Apps, consumption plan, 0 to 1 replicas | $0 (within the monthly free grant) |
| Container image | GitHub Container Registry | $0 |
| Web UI | Vercel, Hobby plan, at `argus.arjunganesh.dev` | $0 |
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
diagram variants match their SVG masters and pass WCAG AA contrast. It builds the container and
runs one demo assessment through it. The Web UI job lints, type-checks, unit-tests and builds
`web/`, then runs its Playwright tests against the API container: the six demo scenarios in light,
dark and phone layouts, each page checked with axe.
