# ARGUS handoff

Read [AGENTS.md](AGENTS.md), this file, then the [v2 plan](docs/ARGUS-V2-PLAN.md). Run the
start-of-session check below before any other work. Update Current state, Next step and Session
log before stopping.

This file is tracked and public. It holds project state only. Drafts and research notes are in
[`docs/research/`](docs/research/README.md). Only account, billing and machine notes stay in
the ignored `.local/` folder.

Copy/paste initialization prompt (with this repository open):

```text
Read AGENTS.md and HANDOFF.md, then docs/ARGUS-V2-PLAN.md. Before anything else, run the start-of-session check in HANDOFF.md: check every fact it records against git, GitHub and the live site, review each pull request opened or merged since the last session-log entry, report every deviation you find, and fix the documents that no longer match. Then continue from Next step. Before stopping, update Current state and Next step in HANDOFF.md and add a Session log entry.
```

## Start-of-session check

Pull requests move faster than the documents that describe them. Before other work, check the
grounded facts and report what deviates, with file and line:

1. **Git and GitHub.** `git fetch --prune`; `main`'s commit and CI result
   (`gh run list --branch main --limit 3`); pull requests merged and open since the last
   session-log entry (`gh pr list --state all --limit 10`), each with its check results; merged
   branches not yet deleted. Compare all of it with Current state and Next step.
2. **Each of those pull requests.** It has a changelog entry that says what became true and how
   it was checked; this file, the README, `docs/`, `web/README.md` and the diagrams describe the
   code it merged; and no earlier entry or page now contradicts it (search for the old value:
   a version, a status such as "not deployed", a count, a name).
3. **The checks that read facts.** `check_docs.py` and `check_versions.py --check` (the
   commands in `AGENTS.md`), and markdownlint as CI's Documentation job runs it
   (`npx markdownlint-cli2 "**/*.md"`, which reads `.markdownlint-cli2.jsonc`).
4. **The live deployment.** <https://argus.arjunganesh.dev> answers, and so does the API's
   `/health` (the request wakes it; it scales back to zero about 12 minutes later). Compare with
   "Live since" below.

Fix each deviation in the documents, or record it under Open items when it needs the
maintainer's decision. Fixes reach GitHub only with the maintainer's go-ahead, like any change.

## Current state — 25 November 2026

- **Source.** `main` is at `9d4e535` (#47, merged on 25 November: the handoff after #46 and
  how a local run signs in to the study model), on top of `16f124d` (#46: the session checks of
  22 and 25 November, the protocol's model and budget, the spending stop and the open items
  fixed on 25 November). Both merged branches are deleted; this file's update is in its own docs
  pull request (`docs/handoff-after-47`).
- **The week 1 baseline command (#44) and its spending stop (#46) are merged.** `python -m argus.study.baseline` runs arm A on the six demo scenarios and
  writes the protocol's run records ([`docs/research/baseline.md`](docs/research/baseline.md)).
  The analyst prompt comes from the production code, split into a prompt builder and a recorded
  call; study calls turn off the OpenAI client's own retries, so a request is sent at most three
  times, as protocol section 8 allows (Codex's review finding on #44). A model run now needs
  `--prices` (recorded in the manifest with their source and check date) and `--ledger` (one
  spend file for the study): each attempt reserves an upper bound on its cost first, settles at
  the reported usage, and the run stops before an attempt that would take the study past US$20
  or week 1 past US$2. One run at a time holds the ledger (a lock file beside it) and rereads it
  once it does, so two runs cannot both spend the last of the budget (Codex's finding on #46);
  the prices file and the ledger are read only from inside the working directory. At the
  approved rates week 1 reserves about US$0.64; 90 failed attempts would count US$1.91. 495 tests pass at 100% coverage; the 25 November offline run wrote 30
  fallback items and spent nothing. No model baseline exists.
- **The analyst workspace is live (#40, #41 and #43).** The site reads a report as a case file (case
  header, sanctions match panel, "Why this score" with each finding's evidence) and lists the
  demo cases with their last run and review state in this browser (A, #40). A visitor can play
  the review: resolve a sanctions match, decide the case with a reason, and have the approver
  sign off a HIGH or CRITICAL decision, all kept in the browser and labelled as a demo (B, #41,
  with a layout fix in the match panel). The public domain serves production from `16f124d`
  (#46, which changed the cold-start notice); the four review fixes came in #43. Vercel skipped
  the builds for #44, #45 and #47, which changed no files under `web/`.
- **Released: `v0.1.0`, 16 November.** The tag is on `874ef46`; the
  [GitHub Release](https://github.com/iarjunganesh/argus/releases/tag/v0.1.0) carries the
  changelog notes. Zenodo archived it as 10.5281/zenodo.24292414; the concept DOI
  10.5281/zenodo.24292413 always resolves to the latest version. The post-release dependency
  refresh (#35) is merged, which finishes the release; Agent Framework moved to 1.26.0 by hand.
- **What runs.** ARGUS is a technical demonstration with no active customers. The v2 study
  uses synthetic cases for a technical report. The FastAPI API runs the five-agent Microsoft
  Agent Framework workflow in one process. The Next.js UI calls the API. Fixed rules compute
  the score and tier from typed findings. A language model writes the explanation. The default
  is the local data plane with synthetic data and no cloud account. Known issues: the Azure data plane has run live only in
  part (the entity store, sanctions and adverse-media searches and Document Intelligence have
  not), and the API takes no documents.
- **Live since 18 November, for the six demo cases.** With the maintainer's go-ahead:
  - **Azure.** The API runs on Azure Container Apps in `rg-argus`, deployed by the Deploy
    workflow on the `v0.1.0` tag (Sweden Central; AI Search in France Central; free tiers; the
    model `gpt-5.4-mini`, pay per token). `infra/populate.py` filled the data plane. Deploy signs
    in as the user-assigned managed identity `id-argus-deploy`, kept in its own group
    `rg-argus-ci` and trusted for the GitHub `azure` environment only (deployments from `main`
    and `v*` tags). The Azure sign-in check (`azure-check.yml`) passed. Because
    `AZURE_RESOURCE_GROUP` is set, the release workflow deploys the API after publishing
    a release from a tag push.
  - **Vercel.** The web UI runs at <https://argus.arjunganesh.dev> (project `argus`, Hobby),
    connected to this repository: Root Directory `web`, Node.js 26; a push to `main` deploys
    production, other branches get previews, and a push that changes nothing under `web/` since
    the branch's last build is skipped. The repository's homepage link points to the site.
  - **Checked.** The smoke check passed on the rerun; Cayman Synth Capital came out CRITICAL 76
    with two regulations cited and a model-written explanation (the first since the rebuild);
    CORS allows the site's browser origin. The API scaled to zero 12 minutes after its last
    request and served an earlier report afterwards from Cosmos DB. The first request after
    idle took 14 to 30 seconds in the deployment smoke check. On 22 November the site and API
    health check both returned HTTP 200, with the API taking 22.4 seconds. On 25 November both
    returned HTTP 200 again; from zero replicas the health check took 44.5 seconds the first
    time, and the second time a browser showed `{"status":"ok"}` within 8 seconds but reported
    the page loaded only after 27 seconds. The README's live API badge links to the running
    app's health check (the address matches the app's ingress); since #46 the badge and the
    site's cold-start notice say that waking can take up to a minute (the notice said about 20
    seconds), and the live site serves the new notice. Azure Monitor recorded zero
    requests and zero replicas on 20 November (UTC). The corresponding daily cost entry was
    read on 22 November and kept in `.local/`.
- **Every demo case is invented (#29).** The data rule is in `AGENTS.md`, with an empty
  `docs/DATA-SOURCES.md` register. The six scenarios keep their tiers: Jane Synthetic 3.0 (LOW),
  Synthetic Holdings B.V. 44.0 (MEDIUM), Cayman Synth Capital 76.0 (CRITICAL), Synthetic
  Payments AG 56.5 (HIGH), Synthetic Nordic Bank A/S 36.0 (MEDIUM), Synthetic Pacific Banking
  Corporation 18.2 (LOW).
- **Typed findings (#31).** Canonical facts and explicit assessment states are the only case
  inputs to the shared score and obligation policy. Reports add `findings`, `evidence` and a
  versioned `decision_record`, pending human review; cached agent scores cannot affect
  decisions. The analyst prompt is unchanged and typed records still contain raw strings, so
  the minimised input is study work. The customer-facing variant is not wired in.
- **Study protocol: drafted, not frozen (#32).**
  [`docs/research/study-protocol.md`](docs/research/study-protocol.md) fixes 24 synthetic cases
  in eight strata (8 tuning, 16 held out), three arms (today's raw prompt, minimised typed
  findings, the fixed template), a per-case reference written before outputs are read, injection
  and missing-step variants with their expected behaviour, the measures and the analysis. About
  770 model calls before retries. The maintainer approved the existing Azure OpenAI
  `gpt-5.4-mini` deployment, version `2026-03-17`, and a US$20 study token-spend ceiling
  including up to US$2 for week 1. On 25 November the deployment read back as that version,
  Data Zone Standard, with automatic upgrades off, and the retail price list still gave the
  recorded rates. Local runs sign in to it with Microsoft Entra ID (the account accepts no
  keys); one test call outside the study on 25 November answered as
  `gpt-5.4-mini-2026-03-17` (see [the baseline guide](docs/research/baseline.md)). The 24
  study cases have yet to be built, and no study model calls have been made.
- **Web UI on Node.js 26 (#39).** CI and the release workflow read `web/.nvmrc`. The
  Vercel project is set to 26.x.
- **Checks.** CI, Attribution and CodeQL pass on `9d4e535`, and CodeQL's Python,
  JavaScript/TypeScript and Actions analyses all uploaded with no error. On `16f124d` the Python
  and JavaScript uploads had failed as GitHub's 25 November incident began, and GitHub refused a
  rerun. Each of #31 through #47 passed all its checks (16 to 18 each). GitHub reports zero open Dependabot, code scanning and secret
  scanning alerts. Since 25 November the `main` ruleset requires ten checks and CodeQL results
  (Decisions, `docs/RELEASING.md`).

## Next step

**The analyst workspace is done (approved 18 November).** The design is in
[`docs/research/analyst-workspace-design.md`](docs/research/analyst-workspace-design.md):

1. **A: done (#40, 19 November).** The cases queue, the case header, the score's working,
   findings with their evidence, the sanctions match panel and the cold-start notice.
2. **B: done (#41, 22 November).** The simulated review kept in the browser (design section 8,
   and "Calls made while building B"). The four minor points from its self-review are fixed
   (#43, 22 November): full storage gets an accurate notice, the Reason field is marked
   required, a form starts afresh when its open steps change, and the header stays whole at
   phone widths.

Waiting for the maintainer: which of the four long Markdown files to shorten, in a docs pull
request of its own: `CHANGELOG.md` (the released `[0.1.0]` section to a summary and a link),
this file (the session log to the last few entries; the unconfirmed schedule), the generated
`docs/DEPENDENCY-REFRESH.md` (only what moved) and `docs/roadmap/durable-execution.md`.

The study proceeds in order:

1. Decide whether to seek a second annotator and include the optional raw arm with no
   finding-count cap (protocol section 16). Then approve the protocol text and date the
   freeze. The frozen version must reach `main` before any study model call.
2. Before the first model run. Done on 25 November: the deployment runs the approved version;
   the command records the sourced prices and enforces the spending stop (tests and an offline
   run); the local `.env` names the `gpt-5.4-mini` deployment with the provider left at `none`
   (it goes on the study command), and a local run signs in with Entra ID (one test call outside
   the study; [`docs/research/baseline.md`](docs/research/baseline.md)). Still open:
   - Whether the study's charges draw on the hackathon credit, and its balance. Microsoft's
     credit documentation says Azure Sponsorship credits might cover models sold directly by
     Azure, `gpt-5.4-mini` among them, and do not cover partner models; the balance shows only
     in the credit's own portal, which needs the maintainer's sign-in. The US$20 ceiling holds
     either way.
   - On the day of the run, recheck the rates and write them to the prices file
     ([`docs/research/baseline.md`](docs/research/baseline.md)), and keep one ledger file for
     every study run.
3. After the freeze: the week 1 baseline (six demo scenarios, arm A, five repeats), then week 2
   (case generator, per-case references, minimised input).

Nothing is pushed, tagged, deployed or paid for without the maintainer's go-ahead in the session.

**Keeping the live demo running.** A merge to `main` that changes `web/` deploys the site on
its own. Fixes the live run needs ship as `v0.1.1` through the release workflow, which then
redeploys the API. `infra/teardown.py` removes the Azure side (see `docs/DEPLOYMENT.md`, "Remove it").

### Proposed schedule (11 November 2026; not yet confirmed by the maintainer)

About three short sessions a week. Calendar weeks 1 and 2 (12 to 25 November: stand-ins, typed
findings, the `v0.1.0` release) are done; the plan's study weeks 1 to 4 follow.

| Calendar week | Dates | Work | Done when |
| --- | --- | --- | --- |
| 3 | 26 Nov–2 Dec | Study protocol frozen; baseline captured; model and budget fixed | The protocol is in Git before any study run |
| 4 | 3–9 Dec | Case set (20 to 30 synthetic cases), per-case reference, minimised input | Cases and expected facts versioned; tuning and held-out cases separated |
| 5 | 10–16 Dec | Matched arms: raw input, minimised input, template control, with repeats | Every request and response saved; structural checks computed |
| 6 | 17–23 Dec | Annotate meaning-level errors; first results note, including failures | Numerators, denominators and examples written down |

January 2027: the injection and missing-step pairs, the one improvement and its rerun, then the
write-up.

## Decisions already made

| ID | Decision |
| --- | --- |
| D1 | Next.js on Vercel Hobby and FastAPI on Azure Container Apps, scaling to zero. Image on GitHub Container Registry, capped logs, no VNet. AI Search on the Free tier first |
| D2 | Latest stable Python (3.14); move to the next minor once every dependency has wheels |
| D3 | `pyproject.toml`, `uv.lock` and `.python-version` |
| D4 | Versioning restarted at `v0.1.0`; the former tags are recorded in the archive |
| D5 | Microsoft Agent Framework. Foundry IQ now; Fabric IQ and Work IQ as MCP tools later |
| D6 | Neutral at the boundaries; the data plane is Azure and local only |

- 28 September 2026: merge commits only on `main`.
- 29 September 2026: no Key Vault (one secret, held by Container Apps); no embedding model;
  Document Intelligence on the free tier although the API takes no documents yet.
- 4 October 2026: synthetic stand-ins and a reworded data rule (done in #29); a public
  deployment accepts the demo cases only and expires reports after 24 hours (merged).
- 11 November 2026 (proposed, not yet confirmed): the study is written up as a short technical
  report with a DOI, about 8 to 12 pages, in late January or February 2027, with an article as
  its summary. A workshop submission is decided only after the results are in.
- 11 November 2026: the two later studies, the public legal-entity cohort, event replay,
  durable execution, Fabric IQ and Work IQ are deferred until the first study is written up.
- 13 November 2026: the data-rule wording is accepted as written, with the empty
  `docs/DATA-SOURCES.md` register and the three stand-in names. ARGUS files name none of the
  author's other projects, not even as cited earlier work.
- 14 November 2026: typed findings are fact-level (one finding per fact, agent scores computed
  from them by the live formulas); the three original recorded profiles' scores may move, their
  tiers may not.
- 16 November 2026: `v0.1.0` is tagged before the first Azure deployment, because the study does
  not need hosting. Fixes the live run needs ship as `v0.1.1`.
- 18 November 2026: the deploy workflow signs in as a user-assigned managed identity, not an app
  registration (the account's right to create one is unconfirmed). It lives in `rg-argus-ci` so
  that a teardown of `rg-argus` keeps it; its role assignments are on `rg-argus` only and are
  repeated after a teardown.
- 18 November 2026: the live demo goes up now rather than in the 23 to 25 November slot. The
  maintainer connected the Vercel project to this repository, so Vercel builds from GitHub (the
  Root Directory is `web`) and pull requests get preview deployments; nothing is uploaded from a
  working copy.
- 18 November 2026: the web UI becomes an analyst's workspace, for a KYC analyst at a bank who
  works cases all day: the report as a case file and a simulated review kept in the browser,
  built together (options A and B in the design). Accounts and stored decisions (option C) are
  out of scope.
- 25 November 2026: merging to `main` requires every CI job: the `main` ruleset now also
  requires Web UI, Container image, Infrastructure template and No AI attribution (ten checks)
  and CodeQL results with no error and no high or critical alert. The API keeps scaling to
  zero; the site and the README's badge say that waking can take up to a minute.

## Open items

- **Manual upgrades the refresh reported.** Node.js 26, the LTS, is done (#39).
  - ESLint 10 and TypeScript 7 are still held back, by the plugins `eslint-config-next` 16.4.6
    depends on (rechecked on 25 November): `eslint-plugin-react` 7.37.5,
    `eslint-plugin-jsx-a11y` 6.10.2 and `eslint-plugin-import` 2.32.0 accept ESLint up to 9,
    and `typescript-eslint` 8.74.0 accepts TypeScript below 6.1.
  - Python 3.15 (3.15.2 is out) is no longer waiting on wheels. `msgspec` 0.22.0 and `pyyaml`
    6.0.4 publish 3.15 wheels for Windows and Linux; the lock still holds 0.21.1 and 6.0.3,
    which the next dependency refresh moves. `uvloop`, never installed on Windows, blocked
    only because the upgrade check asked it for a Windows wheel; #46 fixed that check.
    After the next release's refresh, the release workflow prepares the interpreter pull
    request.
- **A stale contributor entry.** The repository sidebar lists an AI assistant as a contributor.
  The cause is two commits brought in by #1 (June 2026) with co-author trailers; `main` was later
  rewritten and no longer contains them, and GitHub's contributor data for `main` lists only the
  maintainer and Dependabot. Only GitHub Support can remove the leftover commits from #1 and
  refresh the list; the maintainer has the request text.
- **Editor setup.** Use Ruff as the Python formatter, to match the project's formatting checks
  (the recommended VS Code extensions include it); machine-specific diagnostics and suggested
  settings are recorded locally.
- **Documents field.** `v0.1.0` ships with "the API takes no documents" as a known issue; whether
  to add a `documents` field later is undecided.

## Session log

Newest first. Keep about ten entries; older history is in `CHANGELOG.md` and the merged pull
requests.

### 25 November 2026 (latest) — #47 merged

- GitHub reported Actions, pull requests and webhooks operational at 16:37 UTC. With the
  maintainer's go-ahead, pushed #47's last two commits; all 17 checks on its head passed,
  CodeQL included, and the maintainer merged it as `9d4e535` (four commits; the repository
  allows merge commits only, so a single commit needs the branch squashed and force-pushed
  first). On `9d4e535` CI, Attribution and CodeQL pass, with all three CodeQL analyses
  uploaded; zero open code scanning alerts. Vercel skipped the build (no change under `web/`).
- With the maintainer's go-ahead, deleted the merged `docs/handoff-after-46` branch (local and
  on GitHub) and opened this file's update as its own pull request.

### 25 November 2026 — #46 merged

- The maintainer merged #46 (18 checks passing, SonarQube Cloud's gate passed, Codex's thread
  resolved). `main` is at `16f124d`; its CI and Attribution runs pass. CodeQL's Python and
  JavaScript jobs failed while uploading results, with no error logged, although the same
  analysis passed on #46's last commit. GitHub declared an incident at 15:55 UTC (Actions, pull
  requests and Git operations degraded), three minutes later; a rerun was refused with HTTP 500
  twice. The handoff pull request's merge runs CodeQL again. The merge deployed production from
  `16f124d`, the domain points to it, and the site serves the new cold-start notice.
- With the maintainer's go-ahead, deleted the merged `feat/study-spending-stop` branch (local
  and on GitHub). Opening the handoff's pull request failed through both of GitHub's APIs during
  the incident; the maintainer opened it from the web as #47, and its title and description
  were set through the REST API. #47's first CodeQL run failed to start (`startup_failure`),
  GitHub refuses to rerun such a run (HTTP 403), and the `main` ruleset waits for CodeQL
  results, so the branch's next commit, pushed once Actions recovered, starts CodeQL again.
- The maintainer gave their own user the Cognitive Services OpenAI User role on the study
  account (key access is off, and Owner grants no model access), and it read back. With their
  go-ahead, one test call outside the study, through `get_chat_model()` with one attempt and a
  500-token cap, signed in with Entra ID and returned `ready` from
  `gpt-5.4-mini-2026-03-17`, at about US$0.00003 at the protocol's rates. It is not in the
  study ledger, which counts study runs. The baseline guide now says how a local run signs in.

### 25 November 2026 — session check and the spending stop

- Session check. GitHub matches the record: `main` at `041d7ca` with CI, Attribution and
  CodeQL passing, no pull request opened or merged since #45, only `main`, the `v0.1.0` tag and
  release, and no Dependabot, code scanning or secret scanning alert. Vercel's production is
  still #43's `390a86c` (#44 and #45 skipped) and the domain points to it. `check_docs.py`,
  `check_versions.py --check` and markdownlint pass. The site answered at once; the API's
  `/health` answered after 44.5 seconds from zero replicas, beyond the 14 to 30 seconds
  recorded. The maintainer asked whether the README's live API badge opens as expected: its
  address is the app's own, and opened in a browser after the API had scaled to zero again, it
  showed `{"status":"ok"}`; the wait from zero replicas is the open question (Open items).
  Deviations: the 22 November session's changes (its corrections, the protocol's
  model and budget, a test fix) were never committed, so GitHub's copy of this file and the
  protocol still say the model and budget are open; and the local `.env` does not select the
  approved model (Next step).
- Verified the approved deployment (version `2026-03-17`, Data Zone Standard, automatic
  upgrades off) and today's retail rates (unchanged). Microsoft's credit documentation says
  Sponsorship credits might cover models sold directly by Azure; the balance needs the
  maintainer.
- Built the spending stop, test first (`argus.study.spend` and the baseline's `--prices` and
  `--ledger`): 45 new tests, each watched failing first, 479 in all at 100% coverage; ruff,
  mypy, the docs, version and asset checks and markdownlint pass. An offline run with a prices
  file wrote 30 fallback items and nothing to the ledger. Updated the baseline guide, the v2
  plan, the research index, the repository map, the README and the changelog.
- The maintainer asked to fix the open items and open the pull request. Fixed, test first
  where code changed: the refresh now moves the Agent Framework pin itself (five tests); the
  Python upgrade check reads each package's platforms from the lock's markers, so `uvloop` no
  longer blocks Python 3.15 (four tests; the real inventory now lists only `msgspec` and
  `pyyaml`, whose newer releases have the wheels); the site's cold-start notice and the README's
  live API badge say waking can take up to a minute. With the maintainer's explicit approval,
  the `main` ruleset now requires the other four CI jobs and CodeQL results (read back from the
  API). Rechecked ESLint 10 and TypeScript 7: still held back by `eslint-config-next`'s
  plugins. Left open: the stale contributor entry (only GitHub Support can clear it) and the
  documents field (undecided). 495 tests at 100% coverage (after the fixes below), ruff, mypy,
  the docs, version and asset checks, markdownlint, and the web UI's lint, format, type check,
  96 unit tests and build pass; the end-to-end tests run in the pull request's CI (Node 26 is
  not installed here). Committed on `feat/study-spending-stop` and opened #46. All its required checks
  passed; SonarQube Cloud's gate failed on two path traversal findings (the prices file and the
  ledger are read from any path an agent passes), so the command now reads them only from
  inside the working directory, with two tests that failed first. Codex then found (P2) that
  two runs opening the ledger before either writes could both reserve the last of the budget;
  reproduced in a test, fixed with a lock that holds the ledger for a whole run and a fresh read
  once it is held (five tests that failed first), and replied to and resolved its thread.

### 22 November 2026 — model and budget approved

- Confirmed the existing Azure model's version and automatic-upgrade setting and checked
  Microsoft's retail token rates. Proposed a study model and spending ceiling under
  Next step. The maintainer's decision is pending. No study model calls were sent.
- The maintainer confirmed ARGUS is a technical demonstration with no active customers.
  Revised the proposed ceiling to US$20 and recorded how the runner should enforce it.
- Confirmed the published US$500 Azure credit for Hack for Good winners. The study budget
  proposal remains at US$20. Remaining credit and model-charge eligibility are unverified.
- The maintainer approved GPT-5.4 mini and the US$20 ceiling, including US$2 for week 1.
  Recorded the configuration, rates and spending stop in protocol section 8. The next
  decisions concern the second annotator and optional raw arm.

### 22 November 2026 — session check and baseline readiness

- Fetched and checked GitHub. #45 is the only pull request opened or merged after the previous
  entry. It changes only the handoff and passed all 18 checks. Main CI and Attribution pass on
  `041d7ca`. Rechecked #41 through #44, their changelog and guide updates, and the historical
  check totals for #31 through #40. There are no open pull requests, other remote branches or
  open security alerts. The #42 and #45 documentation-only merges recorded state in the
  handoff and carried no changelog entry.
- Corrected the recorded tip of `main`, the active Vercel deployment (#43's `390a86c`), and
  how Vercel's Node.js version is set. The site and the API's `/health` both returned HTTP 200.
  A CORS preflight succeeded for the site and was refused for an unrelated origin. The
  release tag, Zenodo DOI, GitHub rulesets and Azure deployment history matched the records.
  Read the cost entry for a day with zero API requests and replicas and saved it privately.
- Updated the v2 plan for #44 and the current model and local data-plane implementations.
  Dated the workspace design's description of the old UI and clarified the release workflow's
  deploy trigger. The model baseline guide records that price capture and the spending stop
  are still pending, and the protocol links to the current decision list.
  The local check ran six scenarios five times each and produced 30 matched request and
  response records, all labelled fallback with zero requests sent.
- Fixed the Git discovery test for a repo-local pytest temporary directory and excluded
  ignored Superpowers scratch notes from the Markdown glob. The Python suite passed with
  434 tests and 100% line and branch coverage. Documentation, version and asset checks
  passed, as did 96 web unit tests. The installed Node 27 prerelease failed at server
  startup. All 51 Playwright runs passed on Node 26.13.1.
- The protocol stays in draft pending the maintainer's model, budget, annotation and arm
  decisions.

### 22 November 2026 (continued) — B's minor points and the week 1 code

- At the maintainer's request, fixed the four minor points from B's self-review on
  `fix/review-minors`, each with an end-to-end test that failed first, except the stale form
  choice, which no test can produce today (the form is replaced whenever its open steps
  change), so its key is a guard. A browser check at 360 pixels found the header overlapping
  the logo with the first fix; it now wraps below the logo there.
- Built the week 1 code on `feat/study-baseline`, test first: the analyst explanation split
  into `analyst_request` and `request_explanation` (which records the request, model, usage,
  latency and error), the Compliance agent's `prepare` and the workflow's demo responses
  shared, and `argus.study.baseline`, which writes the protocol's section 13 records, retries a
  failed request twice, refuses a non-local data plane and writes no secret. A test checks that
  its prompt equals the workflow's for all six scenarios.
- The maintainer merged #42 and asked for its branch to be deleted. With the go-ahead, pushed
  both branches and opened #43 and #44 (18 checks passing on each). The maintainer merged #43.
  Codex found on #44 that the OpenAI client's own two retries would multiply the study's: up to
  nine requests per item instead of three, only three of them recorded. Study calls now turn
  them off, with tests that failed first; the run manifest records it.
- #44 then showed as blocked: the `main` ruleset requires resolved review threads. The release
  guide and Open items said branch protection was off; two rulesets (`main`, `release tags`)
  have been active since September and October. Corrected both. Replied to and resolved Codex's
  thread, and deleted the merged `fix/review-minors` branch.
- The maintainer merged #44 (18 checks passing). `main`'s CI and Attribution runs on `78f6fde`
  pass; #44 changed nothing under `web/`. Deleted the merged `feat/study-baseline` branch; only
  `main` remains.

### 22 November 2026 — #41 merged

- The maintainer pointed the live domain at #41's preview, reviewed B there and merged #41
  (18 checks passing; SonarQube's gate passed; Codex found nothing). `main`'s CI, Attribution
  and CodeQL runs on `bb1a67e` pass; the merge deployed production and the domain moved to it;
  the site answers with B's role switch. Deleted the merged `feat/analyst-workspace-b` and
  `docs/handoff-after-40` branches; only `main` remains.

### 22 November 2026 — session check, then B built

- Session check: `main` (`2ec6197`) and its CI as recorded; no pull request since #40, which
  passed its 18 checks; only `main` on GitHub; no Dependabot, code scanning or secret scanning
  alert; `check_docs.py` and `check_versions.py --check` pass, and markdownlint passes on every
  tracked file; 412 tests at 100% coverage; the site answers and the API's `/health` answered
  after a 25-second cold start; Vercel's production deployment is the one built from the #40
  merge, and the domain points to it. Deviations: the handoff commit made after #40 was never
  pushed, so `main`'s copy of this file still says #40 is open (it needs the go-ahead to push);
  the design and the research index still said A's pull request was next; this file's check
  named markdownlint as one of the `AGENTS.md` commands, which list none; and the next step
  pointed at "plan tasks 6 to 9" in a plan kept only in one machine's scratch folder (now it
  points at the design). Fixed in the documents. One idle day's cost was not read: the Azure
  command line does not start on this machine.
- Built B on `feat/analyst-workspace-b`, test first: the review's rules (every allowed and
  refused step, and a replay that skips stored steps the rules would refuse), its store (keyed by
  report ID, 24 hours, blocked storage), the review panels, the role switch, the review states in
  the queue and the audit trail, and their end-to-end tests. The calls made while building it are
  in the design. A browser check found the match panel squeezing the listing's values beside a
  long label (an A defect); fixed in its own commit. A self-review found that a recorded step
  was not announced to screen readers; fixed with a test that failed first.
- With the maintainer's go-ahead, pushed `docs/handoff-after-40` and `feat/analyst-workspace-b`
  and opened #41 for both; all 18 checks pass, SonarQube's gate passed and Codex found nothing.
  The maintainer then pointed the live domain at #41's preview build; the site answers with B's
  role switch. Nothing deployed to production or paid for.

### 19 November 2026 — #40 merged

- The maintainer reviewed A on the live site and merged #40 (18 checks passing). Deleted the
  `feat/analyst-workspace-a` branch; only `main` remains. The merge deployed production from
  `2ec6197` and the domain moved to it from the preview. B starts on 20 November.

### 18 to 19 November 2026 — Node.js 26 and the analyst workspace (A)

- #38 (the live deployment in the docs) and #39 (the web UI on Node.js 26) merged with every
  check passing. The README's live badges link to the site and the API's health check. The
  Vercel project shows each commit and builds on Node.js 26.x; the repository's homepage link
  points to the site. Deleted the merged `docs/record-deployment` and `deps/node-26` branches.
- Built A of the analyst workspace on `feat/analyst-workspace-a` (rebased on #39): the report
  opens with the case header, then the sanctions match beside the customer, then "Why this
  score" with each finding's evidence; the audit trail is collapsed; the start page lists the
  demo cases with their last run in this browser; a slow first request says the API is
  starting. Unit tests cover the arithmetic, the finding grouping and labels, the queue store
  and its sorting.
- The first end-to-end run caught a real mismatch: the working rounded each dimension's points
  to one decimal, so Synthetic Holdings B.V. added up to 44.1 against its score of 44. Each
  dimension's points are now exact (a whole score times a whole percentage has at most two
  decimals), the total is the API's score, and where the exact sum has two decimals (Synthetic
  Pacific Banking Corporation: 18.25 against 18.2) the page says the score keeps one.
- The maintainer pointed out that the handoff and guides had fallen behind the merged work.
  Corrected every stale statement found in a review of all tracked Markdown files; shortening
  the long ones waits for the maintainer's answer. At the maintainer's request, added the
  start-of-session check above and put it in the initialization prompt and `AGENTS.md`.
- #40 opened (A). Vercel skipped its preview: the Ignored Build Step compared only the last
  commit, which changed only documents. Within the Vercel setup approved earlier, the step now
  compares with the branch's last successful deployment; the guide says so. `vercel promote`
  then failed too: it rebuilds the preview for production, and the new step skipped that
  rebuild. Pointed the domain at the preview build instead (`vercel alias set`), and checked
  it in a browser: the queue, then Cayman Synth Capital run against the live API, CRITICAL 76
  with the hold notice, the match panel and a working total of 76.
- Review on #40: Codex found that reopening a report re-recorded it with the current time, so an
  older report could replace a newer run in the queue and restart its 24 hours. Runs are now
  dated by the report's `generated_at`, and a newer run is kept. SonarQube flagged `tabIndex` on
  the raw evidence record; it now wraps instead of scrolling, so it needs no focus.

### 18 November 2026 — Azure readiness, the deploy identity and the live demo

- Read-only check of the subscription, the GitHub settings and Vercel: nothing blocks the live
  run. The free-tier slots are unused, the providers the template needs are registered, the
  template's model version is offered in Sweden Central with its quota free, France Central
  takes a Free search service with agentic retrieval, and `infra/main.bicep` builds.
- With the maintainer's go-ahead, created the deploy sign-in (Current state) with the commands
  now in the guide (plus resource tags); the role assignments read back as expected. The guide
  describes the managed identity, and what to repeat after a teardown.
- A deploy sign-in can only be tested from a GitHub job in the `azure` environment, which
  accepts only `main` and tags, and Deploy creates resources as soon as it signs in. Added the
  Azure sign-in check, which signs in the same way and only validates. Ran the same validation
  locally as the owner: it succeeded for the template's 16 resources and created nothing.
  After #37 merged, the check ran on `main` and passed.
- With the maintainer's go-ahead, deployed: Deploy on the `v0.1.0` tag, then
  `infra/populate.py`, then the rerun's smoke step passed. The container package came out public
  on its own, linked to the public repository; the guide now says so. Then the Vercel project,
  first deployed from `web/` with the CLI; its first build failed because `next build`
  type-checked the Playwright tests, which read `tests/fixtures/` outside `web/`, so
  `web/.vercelignore` leaves them out. The maintainer then connected the project to GitHub;
  its first Git build failed without a Root Directory, now set to `web`, with an Ignored Build
  Step and the two variables for previews too. Recorded the deployment in the README, the guides, the two diagrams and the
  changelog, which carries the current known issues.
- Reviewed the live UI as a bank's KYC analyst would. The maintainer chose to build the analyst
  workspace (A and B) and approved its design.
- Deleted the merged `docs/markdown-cleanup` and `docs/deploy-managed-identity` branches.

### 16 November 2026 — Markdown cleanup

- At the maintainer's request, reviewed every tracked Markdown file outside the frozen archive
  for stale or unwanted content. Condensed this handoff (same state, decisions and open items;
  shorter history) and the data-rule proposal and study data design, which are carried out.
  Their real-company names and the mapping from each stand-in to the company it replaced are
  removed; the rule, its reasons and the GLEIF check of the stand-in names remain. Corrected
  statements that predate the merged data rule or the removal of the public adverse-media file
  (roadmap pages, the source notes, the research index) and dropped an unsourced price figure.
  The released `[0.1.0]` changelog section is unchanged.

### 16 November 2026 — typed findings, protocol and the v0.1.0 release

- Published and merged in order, each with every CI check passing: #31 (typed findings), #32
  (the draft study protocol), #33 (release prep), #34 (a handoff note from a separate editor
  formatter review) and #35 (the post-release dependency refresh).
- The protocol was checked against the code before it was written down: only the first 100
  characters of a PEP match reach today's prompt, so the injection uses a corporate flag or a
  typology label; a missing transaction assessment scores 0, the same as a clear one.
- Before the tag, a read-only review of the whole repository found no blocker. Fixed with it:
  a summary at the top of the release notes, a known issue that no live model has written an
  explanation since the rebuild, an absolute link in the notes, the README container wording, an
  unused `.env.example` setting, and the budget amounts in `docs/ARCHITECTURE.md`. Added
  `CITATION.cff`; the maintainer switched on Zenodo archiving. Updated the repository description
  and topics, created the `deps-broken` label and deleted every merged branch.
- With the maintainer's go-ahead, pushed the annotated `v0.1.0` tag. The release workflow
  validated it, reran CI, published the release, skipped the deploy job and opened #35. Zenodo
  minted the DOI with only the maintainer as author.
- #35's Documentation job failed on a bare run link that the release workflow appends after its
  own Markdown gate; Codex's two review comments asked for the exact Agent Framework pin to move
  and for a changelog entry. Fixed all three, removed the redundant web minimatch override, and
  documented the manual Agent Framework step and the first-deploy smoke failure. Replied to and
  resolved both review threads.
- Traced the AI assistant in the repository's contributor sidebar to #1's leftover commits
  (Open items).

### 15 November 2026 — fact-level findings and decision record

- Implemented canonical facts, retained evidence and a pending-review machine decision record;
  all scoring and obligation mappings use those facts, and the live agents share the formulas.
  Missing or skipped assessments and individual tool fallbacks are explicit.
- Re-recorded the six demo scenarios only after asserting the approved scores and unchanged
  tiers and actions.
- An independent review found two missing supporting observations (layering-only detector
  evidence, ownership nodes behind corporate flags); regression tests reproduced both before the
  fix. Recorded demo claims stay labelled as recorded rather than inventing observations.

### 11 to 14 November 2026 — root handoff, security refresh, stand-ins

- Moved the handoff to this tracked root file and the working drafts into `docs/research/`;
  revised the v2 plan around the matched explanation study; audited every Markdown file against
  the code; removed the unused `argus.community` package.
- The security refresh (#27) cleared the advisories that made every pull request's dependency
  audit fail; removing the `shadcn` command-line package (#30) cleared the last one (deepmerge),
  with its stylesheet copied into `web/src/app/shadcn.css`.
- The maintainer accepted the data rule and the stand-in names; the stand-in branch (#29) carried
  them, removed the public adverse-media file and its 12-point boost, and made every demo case
  invented. Mentions of the author's other projects were removed from the plan and the
  durable-execution page.

### 27 September – 16 October 2026 — pre-v2 cleanup (summary)

- Hackathon material archived; CI quality gate, release and dependency-refresh automation added;
  version reset to 0.1.0.
- Runtime rebuilt as one process on Microsoft Agent Framework with a data plane (local and
  Azure), one container image, and the Next.js web UI replacing Gradio.
- Deployment workflow, Bicep template, demo-only mode and 24-hour report expiry merged; nothing
  deployed.
- Attribution check added; SonarCloud findings fixed or accepted; Dependabot security updates
  merged on 15 October.
