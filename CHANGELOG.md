# Changelog

All notable changes to ARGUS are recorded here. The format follows
[Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

An entry states **what became true and how it was checked**, not which files moved.

Versioning restarted at `v0.1.0` on 2026-09-26. The history of the hackathon releases
(`v0.1.0-hackathon` to `v1.6.0`) is kept in
[`archive/hackathon-2026/CHANGELOG-v1.md`](archive/hackathon-2026/CHANGELOG-v1.md), and the former tags
are listed in [`archive/hackathon-2026/README.md`](archive/hackathon-2026/README.md).

## [Unreleased]

### Added

- **A public deployment runs only the synthetic demo cases, and forgets reports after a day.**
  With `ARGUS_DEMO_ONLY=true`, which `infra/main.bicep` sets, the API answers 403 to anything but
  Synthetic Holdings B.V., Jane Synthetic and Cayman Synth Capital with nothing added, so a
  visitor can't enter a real person's details; a site built with
  `NEXT_PUBLIC_ARGUS_DEMO_ONLY=true` shows a notice and only those three cases instead of the
  form. Both are off by default, so local use is unchanged. Reports, statuses and progress events
  now expire 24 hours after their last change in both report stores (Cosmos through the
  `kyc_reports` container's default time to live), and the UI says so. The API and four agents no
  longer log the entity name. Checked: tests for the refusals (other names, other jurisdictions,
  added aliases, dates of birth or registration numbers), case-insensitive acceptance, the setting,
  expiry and its reset on change, logs without names, and that the template's time to live and
  setting match the code; Bicep builds and lints clean; the Cayman smoke and a browser run of the
  demo-only site against a demo-only local API (three cases, no form, CRITICAL report); the 30
  Playwright tests on the default build, whose API log held no entity names.
- **Deployment from GitHub Actions** (`deploy.yml`). It builds the API image, pushes it to GitHub
  Container Registry, deploys `infra/main.bicep` with the image's digest, and runs the synthetic
  Cayman Synth Capital demo against the deployed API, recording the cold start. It signs in to
  Azure with OpenID Connect (no client secret) from a protected `azure` environment. It runs by hand, and
  `release.yml` runs it after each published release once the repository variable
  `AZURE_RESOURCE_GROUP` is set, so tagging deploys the API. A new CI job compiles the template
  and fails on any Bicep linter warning. Checked: actionlint and zizmor (no new findings), the
  template locally; the Cayman smoke passed against an isolated local API, checking its CRITICAL
  tier, agent provenance and regulatory citations. The workflow itself has not run, because
  Azure is not set up for it yet.
- **An Azure deployment that follows decision D1** (`infra/main.bicep`, [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)),
  replacing the hackathon template (AI Search Basic, a `gpt-4o` deployment, a machine learning
  hub). One resource group: Container Apps (Consumption profile, 0 to 1 replicas) pulling the image from
  GitHub Container Registry; Log Analytics with a 0.1 GB daily cap and 30-day retention; AI Search
  Free; Cosmos DB free tier, whose four containers now share the database's 1000 RU/s (the old
  setup gave each container 400 RU/s of its own, 2000 in all, more than the free tier covers); a
  Foundry account with `gpt-5.4-mini` (Data Zone Standard, EU, 10k tokens a minute, which caps
  what a flood of requests to the public API can spend); Document Intelligence F0. Every resource
  is tagged, and the API has startup, readiness and liveness probes. No key
  is stored: the API's managed identity holds the data roles, and key authentication is off on
  Cosmos DB, the model and Document Intelligence; AI Search Free's query key reaches the API as a
  Container Apps secret. `infra/populate.py` fills the indexes, knowledge bases and containers
  with the operator's Entra ID login, and `infra/teardown.py` lists (dry run) or deletes the
  resource group and purges the soft-deleted AI accounts; both refuse anything but a valid
  resource group name before calling `az`, so a value can't be read as an option. Document
  Intelligence's public network access is off while nothing calls it. `populate.py` gives the
  signed-in operator the Cosmos DB data role on its first run, so filling the data plane works
  after a deployment from the workflow too. Each step now leaves its index or container holding
  exactly the current data: rejected records stop the run instead of being counted, and records
  the regenerated data no longer contains are deleted. The unused `pep_list` container is gone
  (no code read it, and most sanctions records it received lacked its partition key), as is the
  upload of adverse media into `kyc_reports`, and `index_sanctions_and_media.py` now indexes the
  adverse media as well as the sanctions when run as a script. `upload_to_cosmos.py` signs in with
  Entra ID when no key is set. Checked: the template builds and lints clean with Bicep 0.43;
  tests for the two scripts' Azure CLI calls and their order, and that the template's partition
  keys are fields of the synthetic records. The design was reviewed against Microsoft's Container Apps and
  AI workload guidance; `docs/ARCHITECTURE.md` records what was applied and what was left out on
  purpose. **Not deployed yet**: that waits for approval.
- **Keyless access to Azure OpenAI and Document Intelligence.** Like Cosmos DB already did, both
  now sign in with Microsoft Entra ID when no key is set: the managed identity when deployed, the
  developer's `az login` locally. `AZURE_OPENAI_API_KEY` and `DOC_INTELLIGENCE_KEY` become
  optional, and one shared credential serves every client, so its tokens are reused instead of
  fetched per query. AI Search still takes a key: the Free tier has no keyless access. Checked:
  tests for both sign-in paths of each client, including the token the model client sends.
- **A web UI that follows each assessment as it runs** (`web/`: Next.js, TypeScript,
  shadcn/ui). Submit an entity or one of the six demo cases; the assessment page draws the
  workflow's fan-out and fan-in from the progress stream, with each agent's state, time and where
  its result came from, then shows the report: tier, score, what set the tier, sanctions
  screening, enhanced due diligence, recommendation and findings; the evidence line (knowledge
  bases answered, or which tools fell back); risk dimensions; the analyst explanation and who
  wrote it; cited regulations; actions; the audit trail and the raw JSON. The browser calls the
  API, which must list the site in `ARGUS_CORS_ORIGINS`. The assessment's URL holds only the
  report ID; the entity's name stays in the browser tab (session storage), out of browser history,
  server logs and referrers. If the API stops answering, the page says so after three
  unanswered tries instead of waiting. Light and dark themes, landmarks, a live region for
  progress, visible focus, reduced motion respected. No npm package's install script runs
  (`--ignore-scripts` and `web/.npmrc`; none of the locked packages has one). Checked: unit tests
  for the API client, the report's wording, the progress reducer, the stream-error decision and
  the remembered name; Playwright runs the six demo scenarios through the site against the API
  container in CI and compares each report with the recorded outcomes, checks the URL carries no
  name and that an unreachable API is reported, in light, dark and phone layouts, and axe finds
  no WCAG 2.2 AA violations on any page. The site's colour pairs pass WCAG AA in both themes (`render_assets.py --check`) and its
  risk colours are the audited palette (`test_accessibility.py`). Not deployed yet.
- **The version inventory covers the web UI's npm packages and Node.js.** `check_versions.py
  --check` requires exact pins that match `package-lock.json`, and one Node.js major
  (`web/.nvmrc`) across `engines`, `@types/node` and the workflows. The post-release refresh moves
  each package to the newest release of its major, relocks, and runs the web checks; a new major
  is reported for a manual update. Dependabot watches `web/` for security updates. Checked by
  offline tests and one live run against the npm registry and nodejs.org.

- **Local OCR through Tesseract.** With the local backend, identity documents (PNG, or PDF,
  whose pages are rendered first) are read by Tesseract and their `Label: value` lines become the
  same fields Document Intelligence gives (name, date of birth, document number, and so on), each
  with its confidence. It needs the new `ocr` dependency group and the Tesseract program; without
  them, or for a file it cannot read (including a truncated image), the document is still
  reported as unread (`fallback`). The container image leaves it out: deployments use Document
  Intelligence. Checked: tests with Tesseract stand-ins; a real Tesseract 5 read of a rendered
  synthetic passport as PNG and as PDF, which CI now runs with Tesseract installed; and once by
  hand over the 48 documents from `generate_ocr_documents.py`: every PDF gave all its fields, the
  degraded PNGs fewer, down to none for the worst.

- **A container image for the API.** The root `Dockerfile` builds a multi-stage `uv` image on the
  pinned Python 3.14 image: runtime dependencies only, from wheels (`--no-build`), a non-root
  user, and a `HEALTHCHECK` on `/health`. `.dockerignore` is an allow-list, so `.env` never
  reaches the build. Checked: a new
  CI job builds the image, runs one demo assessment through it (`scripts/ci/smoke_api.py`: stream,
  report, tier and sources) and waits for the health check; the same passed locally.
- **The version inventory covers the container base images.** `check_versions.py` requires tag
  and digest pins, reports newer releases and rebuilt images from Docker Hub and GitHub Container
  Registry, and the post-release refresh moves them. Checked by offline tests and one live run.

- **An assessment can be followed as it runs.** `GET /api/v1/kyc/stream/{id}` sends server-sent
  events: each agent's start and finish (with its `source` and any fallbacks), then the final
  status. Events are kept in the report store, so a late or reconnecting client (`Last-Event-ID`)
  misses nothing. Checked: tests for replay, resume, 404, a running assessment and the time
  limit, and one assessment streamed by hand through uvicorn.
- **The API contract is pinned.** `tests/test_api_contract.py` compares the OpenAPI document with
  the reviewed `tests/fixtures/openapi.json` and pins the fields of the report and of the
  progress events, checked on reports computed by the real workflow.
- **`GET /health`** answers while the API process is up.

- **SonarQube Cloud analyses every pull request** (automatic analysis, quality gate on new code).
- **Ruff now also checks security, complexity and error handling.** Added rule sets: security
  (`S`, the bandit rules), complexity (`C90`, at most 10 branches per function), async misuse
  (`ASYNC`), broad exception handlers (`BLE`), performance (`PERF`) and pathlib use (`PTH`). Each
  finding was fixed, or kept with a `noqa` comment giving the reason; the only per-directory
  exceptions are `assert` in tests, `random` in the synthetic-data generators and https REST calls
  in the infra scripts. Checked: `ruff check .` passes with the new rules; the dependency
  inventory was run against PyPI and GitHub after its functions were split up.
- **Every tool reads data through one data plane, with a local and an Azure implementation.**
  Four interfaces in `src/argus/data_plane/` (retriever, entity store, report store, OCR);
  `ARGUS_DATA_BACKEND` picks `local` (the default: synthetic data in `data/`, no cloud account)
  or `azure` (AI Search, Cosmos DB, Document Intelligence). Both search the same documents: the
  regulations corpus and the search-document builders moved to `data_plane/corpus.py`, which
  `infra/foundry_iq/` now uploads. Checked: tests for both implementations; the Azure ones run
  against stand-ins for the Azure SDKs, not yet against live services.
- **Every result says where it came from.** Each agent response carries `source` (`computed`,
  `fallback` or `demo_profile`) and names the tools that fell back; the report's audit trace
  collects them with the data backend, counts only knowledge-base searches that answered, and
  `explanation_source` says whether a model or the fixed template wrote the explanation.
  Checked: a provenance test per agent; the web UI's end-to-end tests check each agent's source.
- **One setting chooses the language model:** `ARGUS_MODEL_PROVIDER` is `none` (the default),
  `azure-openai` (through Azure OpenAI's v1 endpoint), `openai` or `github-models`, in
  `src/argus/models.py`. Checked: `tests/test_models.py`.
- **The six demo scenarios are a regression test.** `tests/test_demo_scenarios.py` checks that
  tier, score, dimension scores, findings and recommended actions match what was recorded before
  this refactor. All six matched.
- **The hosting decision (D1) is written down** in `docs/ARCHITECTURE.md`: Container Apps scaling
  to zero, GitHub's container registry, Vercel, and the free tiers of AI Search, Cosmos DB and
  Document Intelligence in Sweden Central, about $0 a month when idle. Estimated from list prices;
  the exit gate observes a real idle day.
- **Release automation validates the tagged commit before publication.** The workflow reuses
  the full CI gate and requires a matching package version and changelog section. Local
  regression tests cover missing, duplicate and mismatched release metadata and prereleases.
  The rerun of CI receives only the Codecov token, the release is published with the runner's
  own `gh` CLI (no third-party action holds write access), and no CI checkout keeps git
  credentials on disk. Checked with actionlint and zizmor.
- **Post-release dependency reviews record failures as well as upgrades.** The refresh prepares
  a PR with the version inventory and gate results, and keeps interpreter upgrades separate.
  Offline fixture tests check version drift, wheel compatibility, action resolution and failed
  refresh reporting. GitHub publication and automatic PR creation await the first approved tag.
- **The standard GitHub community files:** `CONTRIBUTING.md`, `SECURITY.md` (private
  vulnerability reporting, which is enabled on the repository), `CODE_OF_CONDUCT.md`
  (Contributor Covenant 2.1), issue forms, a pull request template with the CI checklist,
  `CODEOWNERS` and `.editorconfig`.
- **One set of instructions for every coding agent.** `AGENTS.md` holds the rules, the commands,
  the definition of done, the post-release dependency refresh and a repository map; `CLAUDE.md`
  imports it and `.github/copilot-instructions.md` points to it, so Claude Code, Codex and
  GitHub Copilot follow the same file. `scripts/ci/check_docs.py` now fails if the repository map
  and the tracked top-level directories disagree (checked by renaming one row).
- **The Copilot coding agent starts with a working environment**
  (`.github/workflows/copilot-setup-steps.yml` installs the locked dependencies). Shared editor
  and agent settings: `.vscode/extensions.json` recommends Ruff, Python and markdownlint;
  `.claude/settings.json` pre-approves the read-only checks.
- **A brand built around the ARGUS eye**, in light and dark themes: README banner, 16:9 title
  card, GitHub social preview, stacked logo and the mark on its own (`assets/brand/`). The mark
  is an open eye in a diamond; five orbiting nodes stand for the five agents.
- **Three architecture diagrams that match the code** (`assets/architecture/`): the current
  runtime with each Azure service marked "live or mock" or "mock today"; one request end to
  end with the scoring weights and thresholds as coded, showing which steps are deterministic
  and which use a language model; and the planned v2 runtime, labelled as not built. They
  replace the Mermaid chart and the ASCII flow in the README.
- **`scripts/ci/render_assets.py`** writes each master's light and dark variants and its PNG/GIF
  exports. `--check` runs in CI: it fails if a variant is out of date or if any declared
  text/background pair is below WCAG AA in either theme. Checked: it caught a 4.49:1 gold on
  the review band before merge, which was darkened to 5.25:1.
- **An architecture page that matches the running code** (`docs/ARCHITECTURE.md`): processes,
  request flow, the demo-profile shortcut and every service fallback, checked against the code.
- **The v2 plan is public** (`docs/ARGUS-V2-PLAN.md`), with its starting evidence taken from the
  code review rather than from the old README.
- **A CI quality gate** (`.github/workflows/ci.yml`) that fails a pull request on: ruff lint or
  format drift, mypy errors, a failing test or line/branch coverage below 100%, a known
  vulnerability in the locked dependency graph (pip-audit), a committed secret (gitleaks), or
  documentation drift (markdownlint plus `scripts/ci/check_docs.py`: broken links, unfinished
  markers, Python version disagreement, unlisted docs, tracked local files).
- **100% line and branch coverage**, enforced (`fail_under = 100`) and mirrored by Codecov
  (`codecov.yml`: project and patch targets 100%). 75 new tests cover every agent's decision
  branches, the API gateway, the client factories, the UI's submit/poll/fetch paths and the
  Community Edition presets. The only exclusion is the UI's `__main__` launch guard. Tests run
  hermetically: `tests/conftest.py` ignores `.env` and removes Azure credentials from the
  environment, so local and CI runs take the same code paths.
- **Reproducible environments:** `pyproject.toml` with dependency groups, `uv.lock` and
  `.python-version` (3.14). CI, local runs and the Windows demo script use the same lock.

### Changed

- **The README badges say what the code does today, in six labelled rows:** repository state
  (CI, the SonarQube Cloud quality gate, Codecov, the latest release, licence, demo video); the
  Microsoft framework and every Azure service ARGUS uses, each with its job (Agent Framework,
  Azure OpenAI for the explanation only, Foundry IQ, AI Search, Cosmos DB, Document Intelligence,
  Container Apps for the API, Azure Monitor for its logs); the web UI (Next.js, React,
  TypeScript, Node.js, Tailwind CSS, shadcn/ui, Playwright, axe, Vercel Hobby); the backend
  (Python, FastAPI, Pydantic, uv, Ruff, Mypy, pytest, Docker, Tesseract); the tier decision D1
  chose for each Azure service (Azure OpenAI Data Zone Standard, the free agentic retrieval
  allowance, AI Search Free, the Cosmos DB free tier, Document Intelligence F0, the Container Apps
  consumption plan, Log Analytics with a daily cap), each opening its pricing page; and live
  hosting, marked not deployed yet, with the web UI's planned address `argus.arjunganesh.dev`
  (also recorded in the hosting decision). Gone: the Gradio badge, "Azure OpenAI GPT-4o" (no model is the
  default, and GPT-4o was the hackathon's), "Azure AI Search Vector" (retrieval goes through
  Foundry IQ knowledge bases), and two logos shields.io no longer draws. Each badge opens the
  component's own page: an Azure product page, a project site or repository (only the licence
  badge opens `LICENSE`). `check_docs.py` fails on a badge that links to a file here or to a
  documentation article, and `check_versions.py --check` on a version badge that disagrees with
  its pin (Agent Framework exactly; Next.js, React, TypeScript, Tailwind CSS, Playwright, axe,
  FastAPI, Pydantic and pytest at major.minor, so a patch or security update never has to touch
  the README; Node.js at `web/.nvmrc`); the post-release refresh moves version badges with the
  pins. Checked: tests for a wrong, a missing
  and a rewritten badge; every badge renders and every badge link answers.

- **Runtime dependencies are only what the API imports:** `faker` moved to the `data` group and
  `httpx` to the `ui` and `dev` groups. `uv sync` still installs every group.

- **One process runs the whole assessment, as a Microsoft Agent Framework workflow.** The
  orchestrator builds a fixed graph with `WorkflowBuilder` (`agent-framework-core` pinned to
  1.19.0): the Identity, Screening, Corporate and Transaction agents run concurrently, then fan in
  to Compliance. The agents are plain functions called in-process; no model routes the workflow.
  A local run is now the API and the web UI (ports 8000 and 3000) instead of seven processes. An agent
  that raises is reported as `unavailable` and the others continue, as before. Checked: the six
  demo scenarios give the same tiers, scores, findings and actions (unchanged fixture), and
  orchestrator tests cover fan-in, failure, demo profiles and event order.
- **The Azure retriever uses Foundry IQ knowledge bases** instead of querying the search indexes
  directly: the retrieve action of the stable 2026-04-01 API, with a semantic intent (minimal,
  extractive retrieval, no model), ranked by the semantic reranker.
  `infra/foundry_iq/create_knowledge_bases.py` now also creates the knowledge sources and the
  knowledge bases. Checked against a stand-in client with the SDK's request models; not yet
  against a live search service.

- **A potential sanctions match holds the case at CRITICAL, whatever the weighted score.**
  Sanctions are not a weighted risk: FATF Recommendation 6 requires funds of listed persons to be
  frozen without delay, and the Wolfsberg Group's sanctions-screening guidance has a person confirm
  or clear each match. The report says what set the tier (`risk_summary.tier_basis`: `score` or
  `sanctions_match`), recommends a hold until a compliance officer confirms or clears the match,
  and says to freeze and report if it is confirmed. The weights and score bands are unchanged.
  Checked: a sanctions-only case (weighted score 21) now reports CRITICAL; the six demo scenarios
  keep every score, and only Cayman Synth Capital changes tier (HIGH to CRITICAL).
- **A PEP match requires enhanced due diligence, whatever the tier** (`risk_summary.edd_required`).
  A PEP-only case could score LOW and be recommended for standard onboarding. PEP status calls for
  measures, not a higher tier (EU AMLR Article 42 and UK MLR regulation 35 for every PEP, FATF
  Recommendation 12 for foreign PEPs; FCA FG25/3: no single factor makes a customer higher risk
  automatically), so the tier stays as scored and the recommendation and actions name senior
  management approval, source of wealth and funds, and enhanced ongoing monitoring. Checked: a
  PEP-only case stays LOW with the EDD recommendation; in the demo scenarios no tier or score
  moved, Synthetic Holdings B.V. gets the EDD recommendation and both PEP scenarios gain the
  monitoring action.
- **The report says whether sanctions screening ran** (`risk_summary.sanctions_screening`:
  `potential_match`, `no_match` or `not_run`). A case whose screening agent failed or whose
  sanctions search fell back is reported as incomplete instead of being recommended for standard
  onboarding. Checked: a test for each way screening can fail to run.
- **Risk scoring is written down** in `docs/ARCHITECTURE.md`, including two rules that were in the
  code but in no document: the Regulatory dimension is estimated from PEP, adverse-media and
  ownership flags, not from retrieved regulations, and adverse media alone adds 12 points when the
  screening score is at least 70 (reached today only by recorded demo profiles).
- **Reports are stored through the report store:** in memory with the local backend, in Cosmos
  DB (`kyc_reports`) with the Azure one, replacing the gateway's module-level dicts.
- **Browser origins allowed to call the API come from `ARGUS_CORS_ORIGINS`** (none by default)
  instead of `*`, and only `GET` and `POST` are allowed. Checked: a request from another origin
  gets no CORS header.
- **A screening hit needs the entity's full name, or one alias, in the retrieved passage.**
  Sanctions queries no longer include the nationality, and adverse-media queries no longer add
  generic words such as "fraud". Checked on the generated data: an unlisted person no longer
  matched a sanctions entry through a shared country code, or adverse media through shared words.
- **Diagrams and docs describe the data plane**, and the retired "mock" wording can't return:
  `scripts/ci/check_docs.py` fails if it appears in the README, `AGENTS.md`, `CONTRIBUTING.md`,
  `docs/` or the image sources (checked with a probe line).
- **Citations are `citation`** (was `foundry_iq_citation`), with the knowledge base named
  `regulations`, `sanctions` or `adverse_media`.
- **Local working files have a durable home, separate from scratch.** The cross-tool handoff and
  the working plans live in the ignored `.local/`, which must never be cleared; `.tmp/` is
  disposable scratch. `AGENTS.md` and the Copilot instructions point to `.local/HANDOFF.md`.
  Checked: `check_docs.py` fails when a file under `.local/` is tracked (tested with a probe file).
- **ARGUS is an installable package in the standard src layout.** The application
  (`agents/`, `api/`, `utils/`, `accessibility/`, `community/`, `config.py`) moved to
  `src/argus/` and installs in editable mode with `uv sync`; imports are `argus.*`. The API
  starts as `uv run uvicorn argus.api.main:app`.
  Checked: `uv build` produces a wheel, all 50 moves are recorded as git renames, and the suite
  passes unchanged at 100% coverage.
- **The repository root went from 16 directories to 8.** Scripts are sorted by role
  (`scripts/dev/`, `scripts/ci/`), the Foundry IQ setup moved to `infra/foundry_iq/`, and the
  roadmap to `docs/roadmap/`.
- **Tests are organised by subject.** The catch-all `test_coverage_boost.py`, `test_tools.py`
  and `test_agents.py` were split into the per-area files; three tests that mixed several
  modules became eight single-subject tests.
- **Python 3.14 and the latest dependency releases.** This crosses majors (openai 3.x,
  azure-search-documents 12.x, azure-ai-projects 2.x). Checked: the suite passes unchanged on
  the new lock.
- **Line endings are normalised to LF** by `.gitattributes`; PowerShell scripts keep CRLF.
- **Hackathon material is archived, not deleted.** Submission runbooks, narration, slides, the
  original architecture spec and the v1 changelog moved to `archive/hackathon-2026/` with
  `git mv`, so their history is preserved.
- **Versioning restarted.** Tags `v1.2.0` to `v1.6.0` were deleted locally and on GitHub; each
  tag's commit is recorded in the archive README. The orphaned `v1.6.0` commit (`9aee081`) was
  checked to have a tree identical to `d2c9380` on `main` before deletion, so no content was lost.
- **The README describes the code as it is.** It adds a status table of what works live, what
  falls back to mock data, and what doesn't work, and removes claims the code didn't support
  (Semantic Kernel, the A2A protocol, Azure AI Foundry Agent Service, a runnable community
  edition, a passing WCAG example).

### Fixed

- **A cited regulation states its whole rule.** Each regulatory trigger was the retrieved
  passage cut at 120 characters, often mid-word ("…whose s"). It is now the passage's first
  sentence, where each passage states its rule, cut at a word and marked with "…" only past 300
  characters; the citation still names the document and article. Checked: tests for the
  sentence split and the cut, every passage in the regulations corpus gives a whole rule, and
  the end-to-end tests check each rule the web UI shows.
- **The v2 diagram says what is built.** It was labelled "planned, not built" although the Agent
  Framework workflow, the container, the data plane, the model setting and the web UI exist.
  Built parts are now drawn solid and planned ones dashed, under "partly built, not deployed".

- **Explanations work with GPT-5 and o-series models.** They reject `max_tokens` and
  `temperature`, so every explanation from the planned `gpt-5.4-mini` deployment would have
  fallen back to the template. Reasoning models now get `max_completion_tokens` only;
  `ARGUS_MODEL_REASONING` (`auto`, `true`, `false`) says which kind the model is. The prompts are
  unchanged. Checked by tests on the arguments sent; not yet against a live model.
- **`scripts/dev/start_demo.ps1` parses again**: a corrupted line had broken it.

- **The Cosmos transactions query passes its row limit as a query parameter** instead of
  formatting it into the SQL text. The value was already an integer, so this was not exploitable.
  Not yet run against a live Cosmos account.
- **The dependency inventory can only fetch from PyPI and the GitHub API,** and percent-encodes
  every path segment it reads from repository files (package names, action repositories, tags),
  so none can change the request path. Found by SonarQube Cloud (path traversal in
  `check_versions.fetch`). Checked: a test for the host allow-list and the encoding; the live
  inventory report is unchanged.
- **The WCAG contrast check raises instead of using `assert`,** so it still runs under
  `python -O`.
- **The report no longer shows a confidence it never computed.** Every report said 83%
  (`risk_summary.confidence`), and every PEP finding said 0.92; both were fixed numbers. The
  report shows what set the tier and the sanctions screening status instead.
- **The regulations knowledge base says what its sources say.** Checked against the published
  texts: FATF Recommendation 20 no longer carries two sentences that are not in it; the 6th AML
  Directive's predicate offences are cited to Article 2, not Article 3; the enhanced due diligence
  entry names 4AMLD Article 18a; the DORA entry separates Article 5 from Article 6; the Wolfsberg
  entry is the AML Principles for Private Banking, which it quotes; and FATF Recommendation 12
  now includes family members and close associates. FATF Recommendation 6 (targeted financial
  sanctions) was missing and is added, so a sanctions case can cite it.
- **Unknown entities no longer get invented evidence.** When a data service was unavailable,
  tools returned fabricated positives: a registry match (`MOCK-001`), a 51% beneficial owner, a
  transaction history with a structuring pattern for any name, OCR fields that then failed the
  name check, and typology citations to report chapters that weren't retrieved. They now return
  results that assert nothing, labelled `fallback`. Checked: a fallback test per tool.
- **An outage is no longer presented as regulatory evidence.** When the regulations search was
  unavailable, or found nothing relevant, the report cited a fixed FATF Recommendation 10 text as
  if it had been retrieved. It now lists no regulatory triggers, and the fallback is named in the
  audit trace. Checked: a test for each path.
- **A typology search that falls back is reported.** The transaction agent said `computed` even
  when `typology_matcher`'s search was unavailable; it now says `fallback` and names the tool.
- **Settings in `.env` take effect in every service.** The gateway (CORS origins), the data plane
  (backend) and the model factory now load the repository's `.env` themselves; before, a service
  that didn't happen to import another loader ignored them. Checked: a test that each module
  loads it on import.
- **The Azure Cosmos containers are partitioned on fields the uploaded records have:**
  `corporate_graph` on `/parent_entity` and `transactions` on `/entity_name` (was `/entity_id`,
  which neither record type carries). Checked: a test against the synthetic record shapes.
- **The audit trace no longer reports fixed counts.** `tool_calls` was always 15 and the
  knowledge-base query count always 3; the count is now of searches that answered.
- **OCR can reach Document Intelligence.** It uses `azure-ai-documentintelligence` and the
  prebuilt ID model; before, it imported a package that wasn't installed. Not yet run live.
- **Risk and status badges now meet the normal-text AA contrast threshold.** Darker green,
  amber and red tokens replace the failing palette; the UI uses the shared audited pairs
  with explicit white text on colored backgrounds. The formerly expected failure now passes,
  and rendered-HTML checks cover each risk tier and status, including unknown values. This
  verifies badge contrast, not full UI accessibility.
- **Structured logs now include their context fields.** `JsonFormatter` looked for a single
  `record.extra` attribute that `logging` never sets, so every `extra=` field (task IDs, report
  IDs, entity names) was silently dropped. Checked: `tests/test_structured_logger.py`.
- **The test suite runs from the repository root.** The empty root `__init__.py` made pytest
  treat the parent directory as the import root. Checked: 50 passed, 1 xfailed.

### Removed

- **The Gradio UI** (`src/argus/ui/`, the `ui` dependency group and the 29 packages only it
  needed), replaced by the web UI, which shows everything it did plus live progress. Its static
  "OCR visibility" box is gone: it described document uploads the API does not accept. Checked:
  the web UI's end-to-end tests cover the six demo scenarios the Gradio page offered.

- **The five per-agent FastAPI services and their custom `/a2a/invoke` JSON envelope** (never the
  A2A protocol), the `*_AGENT_URL` settings, and the admin endpoints that listed and polled the
  services (`/api/v1/admin/agents`, `/api/v1/admin/health`).

- **`azure-ai-projects`**, which only backed a knowledge-base call that didn't exist, and the old
  model settings `USE_GITHUB_MODELS` and `AZURE_OPENAI_API_VERSION` (replaced by
  `ARGUS_MODEL_PROVIDER`). Also an unused orchestrator system prompt.
- **Every `sys.path` hack** (9 files): scripts now import the installed `argus` package.
- **`observability/`**, which held only a "planned" note (OpenTelemetry is in the v2 plan), and
  **`scripts/create_test_doc.py`**, which nothing used. The Community Edition compose file left
  the Python package and is kept as a labelled sketch in `docs/roadmap/`.
- **Hackathon-era images and the scripts that made them** (the pentagon logo, the Mermaid
  architecture sources, the 1300×500 banner and GIFs, `build_animated_diagram.py`,
  `capture_gif_frames.js`) moved to `archive/hackathon-2026/` with `git mv`.
- **Unreachable code:** a `try/except` around plain dictionary reads in `risk_scorer`, and an
  empty-JSON guard in the UI that `json.dumps` can never trigger.
- **Unused dependencies:** semantic-kernel, pandas, numpy, networkx, tenacity, rich,
  asyncio-throttle, opentelemetry-sdk, azure-monitor-opentelemetry, azure-ai-inference,
  azure-ai-documentintelligence, python-multipart, pytest-httpx, requests. Checked: nothing imports
  them.
- **`infra/setup.ps1` and `infra/create_cosmos_db.py`**, the hackathon setup: the first wrote
  every service's key into `.env`; the template now creates the Cosmos DB containers, and
  `infra/populate.py` does the rest without keys on disk.
- **`requirements.txt`, `.coveragerc` and `python-tests.yml`**, replaced by `pyproject.toml`,
  `uv.lock` and `ci.yml`.
- **Generated files are no longer tracked:** `coverage.xml` and `data/reports_batch.jsonl`.

### Known issues

- **The API does not accept identity documents yet.** `POST /api/v1/kyc/assess` has no
  documents field, so OCR (local or Document Intelligence) runs only when the Identity agent is
  called directly with `documents`, as the tests do.
- **The Azure data plane has not run against live services.** AI Search, Cosmos DB and Document
  Intelligence are tested against stand-ins for their SDKs; they are verified during deployment.
- **ARGUS does not tell foreign from domestic PEPs.** It requires enhanced due diligence for
  every PEP (the EU and UK rule), which is stricter than FATF Recommendation 12 for domestic PEPs
  in lower-risk relationships.
