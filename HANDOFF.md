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
3. **The checks that read facts.** `check_docs.py`, `check_versions.py --check` and markdownlint
   (the commands in `AGENTS.md`).
4. **The live deployment.** <https://argus.arjunganesh.dev> answers, and so does the API's
   `/health` (the request wakes it; it scales back to zero about 12 minutes later). Compare with
   "Live since" below.

Fix each deviation in the documents, or record it under Open items when it needs the
maintainer's decision. Fixes reach GitHub only with the maintainer's go-ahead, like any change.

## Current state — 19 November 2026

- **Source.** `main` is at `ef76ace` (#39 merged). Its CI passes. In progress on
  `feat/analyst-workspace-a`: the analyst workspace's first pull request (Next step).
- **Released: `v0.1.0`, 16 November.** The tag is on `874ef46`; the
  [GitHub Release](https://github.com/iarjunganesh/argus/releases/tag/v0.1.0) carries the
  changelog notes. Zenodo archived it as 10.5281/zenodo.24292414; the concept DOI
  10.5281/zenodo.24292413 always resolves to the latest version. The post-release dependency
  refresh (#35) is merged, which finishes the release; Agent Framework moved to 1.26.0 by hand.
- **What runs.** One process: a FastAPI API that runs five agents as a Microsoft Agent Framework
  workflow, and a Next.js web UI. Fixed rules compute the score and tier from typed findings; a
  language model only writes the explanation. The default is the local data plane with
  synthetic data and no cloud account. Known issues: the Azure data plane has run live only in
  part (the entity store, sanctions and adverse-media searches and Document Intelligence have
  not), and the API takes no documents.
- **Live since 18 November, for the six demo cases.** With the maintainer's go-ahead:
  - **Azure.** The API runs on Azure Container Apps in `rg-argus`, deployed by the Deploy
    workflow on the `v0.1.0` tag (Sweden Central; AI Search in France Central; free tiers; the
    model `gpt-5.4-mini`, pay per token). `infra/populate.py` filled the data plane. Deploy signs
    in as the user-assigned managed identity `id-argus-deploy`, kept in its own group
    `rg-argus-ci` and trusted for the GitHub `azure` environment only (deployments from `main`
    and `v*` tags). The Azure sign-in check (`azure-check.yml`) passed. Because
    `AZURE_RESOURCE_GROUP` is set, **every published release now deploys automatically**.
  - **Vercel.** The web UI runs at <https://argus.arjunganesh.dev> (project `argus`, Hobby),
    connected to this repository: Root Directory `web`, Node.js 26; a push to `main` deploys
    production, other branches get previews, and a push that changes nothing under `web/` since
    the branch's last build is skipped. The repository's homepage link points to the site.
  - **Checked.** The smoke check passed on the rerun; Cayman Synth Capital came out CRITICAL 76
    with two regulations cited and a model-written explanation (the first since the rebuild);
    the API refuses other origins; it scaled to zero 12 minutes after its last request, and a
    report made before that was served afterwards from Cosmos DB. The first request after idle
    takes 14 to 30 seconds. One idle day's cost is still to be read.
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
  770 model calls. Its model configuration and budget ceiling are open. No case, model call or
  result exists.
- **Web UI on Node.js 26 (#39).** CI, the release workflow and Vercel read the version from
  `web/.nvmrc`.
- **Checks.** Every pull request merged since 16 November (#31 to #39) passed all its CI checks
  (16 to 18 each): 412 tests at 100% line and branch coverage, type check, lint, documentation,
  the web UI with its Playwright and axe tests, container image, dependency audit, CodeQL and
  SonarQube Cloud. No Dependabot, code scanning or secret scanning alert is open.

## Next step

**The analyst workspace, now (approved 18 November).** The design is in
[`docs/research/analyst-workspace-design.md`](docs/research/analyst-workspace-design.md). Two
pull requests:

1. **A**, built on `feat/analyst-workspace-a`: the cases queue, the case header, the score's
   working, findings with their evidence, the sanctions match panel and the cold-start notice.
   Pull request #40 (with the design). Its preview build serves <https://argus.arjunganesh.dev>
   (`vercel alias set`, see `docs/DEPLOYMENT.md`) for the maintainer's review on the live site;
   merge it, or point the domain back at the latest production deployment.
2. **B**, after A is merged: the simulated review kept in the browser, reviewed the same way.

Web UI only: the API, the score and the demo profiles do not change.

The study, after that. Maintainer decisions still open:

1. The study's model configuration and budget ceiling (protocol section 8). Required to freeze
   the protocol and before any study model call.
2. Whether a second annotator is sought, and whether the optional uncapped raw arm is included
   (protocol section 16).

Then, in order:

1. Freeze the protocol once decisions 1 and 2 are made and the text is approved: its status
   line says "frozen" with the date, and that version reaches `main` before any study model
   call.
2. Week 1 code, which can start before the freeze because it makes no model call: a documented
   baseline command that takes the analyst prompt from the production code path (split
   `explain_decision()` into a prompt builder and the call) and writes the run records in
   protocol section 13. Exercise it with `ARGUS_MODEL_PROVIDER=none`; those outputs are
   labelled fallback and are not a model baseline.
3. After the freeze and the budget: the week 1 baseline (six demo scenarios, arm A, five
   repeats), then week 2 (case generator, per-case references, minimised input).

Nothing is pushed, tagged, deployed or paid for without the maintainer's go-ahead in the session.

**Keeping the live demo running.** Read one idle day's cost (Cost Management lags by up to a
day). A merge to `main` that changes `web/` deploys the site on its own. Fixes the live run needs ship as
`v0.1.1`; publishing that release redeploys the API automatically. `infra/teardown.py` removes
the Azure side (see `docs/DEPLOYMENT.md`, "Remove it").

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

## Open items

- **Manual upgrades the refresh reported.** Node.js 26, the LTS, is done (#39). ESLint 10
  and TypeScript 7 are major versions, held back by peer limits
  (`eslint-config-next` matches Next.js 16.4.6). Python 3.15 waits for wheels of msgspec,
  pyyaml and uvloop.
- **The refresh does not move Agent Framework.** It keeps the exact pin at its locked version, so
  each refresh moves it by hand (documented in `docs/RELEASING.md`); automating that step is
  open.
- **A stale contributor entry.** The repository sidebar lists an AI assistant as a contributor.
  The cause is two commits brought in by #1 (June 2026) with co-author trailers; `main` was later
  rewritten and no longer contains them, and GitHub's contributor data for `main` lists only the
  maintainer and Dependabot. Only GitHub Support can remove the leftover commits from #1 and
  refresh the list; the maintainer has the request text.
- **Branch protection** on `main` is off and needs its own approval (`docs/RELEASING.md`).
- **Editor setup.** Use Ruff as the Python formatter, to match the project's formatting checks
  (the recommended VS Code extensions include it); machine-specific diagnostics and suggested
  settings are recorded locally.
- **Documents field.** `v0.1.0` ships with "the API takes no documents" as a known issue; whether
  to add a `documents` field later is undecided.

## Session log

Newest first. Keep about ten entries; older history is in `CHANGELOG.md` and the merged pull
requests.

### 18 to 19 November 2026 (latest) — Node.js 26 and the analyst workspace (A)

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
