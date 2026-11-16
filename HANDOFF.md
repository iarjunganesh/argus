# ARGUS handoff

Read [AGENTS.md](AGENTS.md), this file, then the [v2 plan](docs/ARGUS-V2-PLAN.md). Update Current
state, Next step and Session log before stopping.

This file is tracked and public. It holds project state only. Drafts and research notes are in
[`docs/research/`](docs/research/README.md). Only account, billing and machine notes stay in
the ignored `.local/` folder.

Copy/paste initialization prompt (with this repository open):

```text
Read AGENTS.md and HANDOFF.md, then docs/ARGUS-V2-PLAN.md, and continue from Next step. Before stopping, update Current state and Next step in HANDOFF.md and add a Session log entry.
```

## Current state — 16 November 2026

- **Source.** `main` is at `874ef46`, tagged `v0.1.0`. On 16 November the maintainer merged
  #31 (typed findings), #32 (the draft study protocol), #33 (the release prep) and #34 (a
  handoff note), each after all CI checks passed. The release workflow's `deps: refresh after
  v0.1.0` pull request (#35) is open, with follow-up commits for the review comments; it is not
  merged. No deployment or paid model run.
- **Security refresh.** #30 removed the package that brought in deepmerge; its recorded checks
  found no npm advisories. On 16 November there were no open Dependabot, code scanning or
  secret scanning alerts.
- **Stand-ins and data rule: merged (#29).** Synthetic Payments AG (HIGH,
  56.5), Synthetic Nordic Bank A/S (MEDIUM, 36.0) and Synthetic Pacific Banking Corporation
  (LOW, 18.2) replace the three real-company profiles. Their profile scores are what the live
  agents compute from their facts (a test recomputes them). All six demo cases are invented, so
  demo-only mode accepts all six. `AGENTS.md` carries the accepted data rule, with an empty
  `docs/DATA-SOURCES.md`. The public adverse-media file and the 12-point adverse-media boost are
  removed.
- **What runs.** One process: a FastAPI API that runs five agents as a Microsoft Agent Framework
  workflow, and a Next.js web UI. Fixed rules compute the score and tier; a language model only
  writes the explanation. The default is the local data plane with synthetic data and no cloud
  account. The Azure data plane exists but is not verified against live services, and no live
  model has written an explanation since the rebuild (both are known issues).
- **Released: `v0.1.0` (16 November); not deployed.** With the maintainer's go-ahead, the
  annotated tag was pushed on `874ef46`. The release workflow validated it, reran CI, published
  the [GitHub Release](https://github.com/iarjunganesh/argus/releases/tag/v0.1.0) with the
  changelog notes, skipped the deploy job (no `AZURE_RESOURCE_GROUP`) and opened #35. Zenodo
  archived it as 10.5281/zenodo.24292414 (concept DOI 10.5281/zenodo.24292413), with the author and metadata from
  `CITATION.cff`. The release is finished once #35 is merged. The deployment workflow and Bicep
  template are merged; no Azure or Vercel resource has been created.
- **Typed findings: merged (#31).** Canonical facts and explicit assessment states are the only
  case inputs to one shared score/obligation policy. Reports add `findings`, retained
  `evidence` and a versioned `decision_record`, pending human review; cached numeric agent
  scores cannot affect decisions. Jane now scores 3.0 (LOW), Synthetic Holdings 44.0 (MEDIUM),
  Cayman 76.0 (CRITICAL); all six tiers and recommended actions are unchanged. The analyst
  prompt template is unchanged; typed records still contain raw strings, so the minimised input
  is study work. The customer-facing variant is still not wired in.
- **Study protocol: drafted, not frozen.** [`docs/research/study-protocol.md`](docs/research/study-protocol.md)
  (merged as a draft in #32) fixes 24 synthetic cases in eight strata (8 tuning, 16 held out), arms A
  (today's raw prompt), B (minimised typed findings, no entity name or free text) and C (the fixed
  template), the per-case reference written before outputs are read, two injection and two
  missing-step variants on six cases each with their expected behaviour, the structural and
  annotated measures, the analysis and the run records. About 770 model calls in all. Its model
  configuration and budget ceiling are left open. No case, model call or result exists.
- **Verification.** #31 to #34 each passed every CI check (tests and 100% coverage, type
  check, lint, documentation, web UI, container image, dependency audit, CodeQL, SonarQube Cloud,
  Codecov, attribution, secret scan). On #35 every check passed except Documentation, a bare run
  link the release workflow appends after its own Markdown gate; that and the two review comments
  are fixed in its follow-up commits. Agent Framework 1.26.0 passes all 412 tests locally at
  100% coverage.
- **Editor integration reviewed.** Python formatting uses Ruff in CI and the recommended VS
  Code extensions. The local formatter-log review found no need for an application change.

## Next step

Maintainer decisions still open:

1. The study's model configuration and budget ceiling (protocol section 8). Required to freeze
   the protocol and before any study model call.
2. Whether a second annotator is sought, and whether the optional uncapped raw arm is included
   (protocol section 16).

Then, in order:

1. Finish `v0.1.0`: once #35's CI is green and its review comments are answered, the
   maintainer merges it.
2. Freeze the protocol once decisions 1 and 2 are made and the text is approved: its status
   line says "frozen" with the date, and that version reaches `main` before any study model
   call.
3. Week 1 code, which can start before the freeze because it makes no model call: a documented
   baseline command that takes the analyst prompt from the production code path (split
   `explain_decision()` into a prompt builder and the call) and writes the run records in
   protocol section 13. Exercise it with `ARGUS_MODEL_PROVIDER=none`; those outputs are
   labelled fallback and are not a model baseline.
4. After the freeze and the budget: the week 1 baseline (six demo scenarios, arm A, five
   repeats), then week 2 (case generator, per-case references, minimised input).

Nothing is pushed, tagged, deployed or paid for without the maintainer's go-ahead in the session.

**The first live run (proposed for 23 to 25 November).** Before the protocol freeze and
baseline in calendar week 3; it still needs its own approvals.

- *Live run:* approve the resources in `docs/DEPLOYMENT.md`; create the workflow identity (a
  user-assigned managed identity with a federated credential avoids the unknown
  app-registration permission), the `azure` environment and the variable; run Deploy on the tag,
  fill the data plane (the first deploy's smoke step fails until it is filled), run the smoke
  check, confirm zero replicas after 30 idle minutes, read one
  idle day's cost; then the Vercel project, its origin in `corsOrigins` and the docs updates
  listed under "Open items". Fixes the live run needs ship as `v0.1.1`.

### Proposed schedule (11 November 2026; not yet confirmed by the maintainer)

About three short sessions a week. The plan's study weeks 1 to 6 start in calendar week 3 below,
because the two prerequisites come first.

| Calendar week | Dates | Work | Done when |
| --- | --- | --- | --- |
| 1 | 12–18 Nov | Merge the security refresh and the handoff branch; stand-ins and the reworded rule (data-rule questions answered 13 Nov) | No real company is a demo case; CI green |
| 2 | 19–25 Nov | Typed findings as the only inputs to scoring; tag `v0.1.0` if it does not wait for deployment | Demo tiers unchanged; every score traces to finding identifiers |
| 3 | 26 Nov–2 Dec | Study protocol committed; baseline captured; model and budget fixed | The protocol is in Git before any study run |
| 4 | 3–9 Dec | Case set (20 to 30 synthetic cases), per-case reference, minimised input | Cases and expected facts versioned; tuning and held-out cases separated |
| 5 | 10–16 Dec | Matched arms: raw input, minimised input, template control, with repeats | Every request and response saved; structural checks computed |
| 6 | 17–23 Dec | Annotate meaning-level errors; first results note, including failures | Numerators, denominators and examples written down |

January 2027: the injection and missing-step pairs, the one improvement and its rerun, then the
write-up. If the typed-findings change takes longer than one week, cut the case set to 20 and
keep the protocol date.

Status on 16 November: calendar weeks 1 and 2 are done (typed findings merged a week early; the
`v0.1.0` released on 16 November), and the week 3 protocol is drafted.

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
- 4 October 2026: synthetic stand-ins and the data-rule change (not yet implemented); a public
  deployment accepts the demo cases only and expires reports after 24 hours (merged).
- 11 November 2026 (proposed, not yet confirmed): the study is written up as a short technical
  report with a DOI, about 8 to 12 pages, in late January or February 2027, with an article as
  its summary. A workshop submission is decided only after the results are in.
- 11 November 2026: the two later studies, the public legal-entity cohort, event replay,
  durable execution, Fabric IQ and Work IQ are deferred until the first study is written up.
- 16 November 2026: `v0.1.0` is tagged before the first Azure deployment; the study does not
  need hosting. The live run follows, and the fixes it needs ship as `v0.1.1`.
- 14 November 2026: typed findings are fact-level (one finding per fact, agent scores computed
  from them by the live formulas); the three original recorded profiles' scores may move, their
  tiers may not.
- 13 November 2026: the data-rule wording is accepted as written, the empty
  `docs/DATA-SOURCES.md` register is added with it, and the stand-ins are Synthetic Payments AG,
  Synthetic Nordic Bank A/S and Synthetic Pacific Banking Corporation (all on the stand-in
  branch). One security-refresh pull request replaces Dependabot's #25 and #26. ARGUS files name
  none of the author's other projects, not even as cited earlier work.

## Open items

- **Editor setup.** Use Ruff as the Python formatter, to match the project's formatting checks
  (the recommended VS Code extensions include it); machine-specific diagnostics and suggested
  settings are recorded locally.
- **A stale contributor entry.** The repository sidebar lists an AI assistant as a contributor.
  The cause is two commits brought in by #1 (June 2026) with co-author trailers; `main` was later
  rewritten and no longer contains them, and GitHub's contributor data for `main` lists only the
  maintainer and Dependabot. Only GitHub Support can remove the leftover commits from #1 and
  refresh the list; the maintainer has the request text.
- **Deployment, when approved.** Steps are in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md): approve
  the resources it lists, set up the workflow identity and the GitHub `azure` environment, deploy,
  fill the data plane, run the smoke check with its cold-start time, confirm zero replicas after
  30 idle minutes and observe one idle day's cost. Then the Vercel project (root `web`, variables
  `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_ARGUS_DEMO_ONLY=true`). When live, update the README
  hosting badges, the ARCHITECTURE hosting heading and the CHANGELOG known issue.
- **Manual upgrades the refresh reported.** Node.js 26 is now the LTS: move `web/.nvmrc` and
  `@types/node` by hand. ESLint 10 and TypeScript 7 are major versions, held back by peer limits
  (`eslint-config-next` matches Next.js 16.4.6). Python 3.15 waits for wheels of msgspec,
  pyyaml and uvloop. The minimatch override is removed in #35.
- **The refresh does not move Agent Framework.** It keeps the exact pin at its locked version, so
  each refresh moves it by hand (documented in `docs/RELEASING.md`); automating that step is
  open.
- `v0.1.0` ships with "the API takes no documents" as a known issue. Whether to add a
  `documents` field later is undecided.

## Session log

Newest first. Keep about ten entries; older history is in `CHANGELOG.md` and the merged pull
requests.

### 16 November 2026 (latest) — v0.1.0 released, refresh reviewed

- With the maintainer's go-ahead, pushed the annotated `v0.1.0` tag on `874ef46` after #34 was
  merged. The release workflow passed: validate, the full CI rerun, publish; deploy was skipped;
  the refresh opened #35. GitHub's webhook log showed Zenodo accepting the release, and its
  public record lists DOI 10.5281/zenodo.24292414 (concept 10.5281/zenodo.24292413) with only the maintainer as author.
- Deleted the merged `chore/release-v0.1.0` and `docs/handoff-editor-note` branches.
- #35: its Documentation job failed on a bare run link that the release workflow appends after
  its Markdown gate. Codex's two review comments asked for the exact Agent Framework pin to move
  and for a changelog entry. Added commits: Agent Framework 1.19.0 → 1.26.0 (412 tests, ruff and
  mypy pass locally), the run link written as `<…>` in the report and in `release.yml`, the
  `[Unreleased]` entries, the redundant web minimatch override removed, and, at the maintainer's
  request, a docs pass: the citation DOI in the README and `CITATION.cff`, the Agent Framework
  step and finished one-time setup in `docs/RELEASING.md` and `AGENTS.md`, the first-deploy
  smoke failure in `docs/DEPLOYMENT.md`, and this handoff.

### 16 November 2026 (night) — editor formatter diagnosis, #33 merged

- Reviewed the supplied formatter log against the installed extension and the repository's
  Ruff configuration, CI and test fixtures. Recorded machine-specific findings in `.local/`;
  recommended aligning editor formatting with Ruff. No application or editor setting changed.
- The maintainer merged #33 (`f1977b7`). This note was absorbed into a small follow-up pull
  request, since #33 could no longer take it. Traced the AI assistant in the repository's
  contributor sidebar to #1's leftover commits (Open items). The `v0.1.0` tag is not pushed yet.

### 16 November 2026 (late evening) — protocol merged; v0.1.0 release prepared

- The maintainer merged #32 (all 16 checks passed); deleted the local branch.
- Asked when to tag and go live, checked the release and deployment setup read-only: no tag,
  no `deps-broken` label, `DEPS_BOT_TOKEN` present, no branch protection, no `azure` environment
  or `AZURE_RESOURCE_GROUP` variable, no `rg-argus` resource group. Proposed tagging `v0.1.0`
  first and the first live run the week after (Next step).
- The maintainer approved the tag plan. Created the `deps-broken` label, dated the changelog
  section `[0.1.0] - 2026-11-16` under a new empty `[Unreleased]`, made the release wording in
  `docs/RELEASING.md` and a README comment true once tagged, and opened the release-prep pull
  request. `uv lock --check`, the release-notes extraction and every check passed. No tag yet.
- At the maintainer's request, scouted the whole repository before merging the release-prep
  pull request (read-only): docs against code, the release and deploy workflows, settings and
  alerts. No blocker; open Dependabot, code scanning and secret scanning alerts were all zero
  (CodeQL alert #1 had already been dismissed as a false positive).
- With the maintainer's approval, added to the release-prep pull request: a summary at the top
  of the `[0.1.0]` notes, a known issue that no live model has written an explanation since the
  rebuild (and the README status row to match), an absolute link in place of the notes' one
  relative link, the README container wording, a `.env.example` without the unused
  `AZURE_RESOURCE_GROUP`, the budget amounts removed from `docs/ARCHITECTURE.md` (earlier
  versions keep them in history), and `CITATION.cff`. The maintainer switched on the Zenodo
  archive for this repository, so the release gets a DOI. Updated the repository description
  and topics (no A2A or Semantic Kernel) and deleted the merged `feat/typed-findings` and
  `docs/study-protocol` branches on GitHub.

### 16 November 2026 (evening) — typed findings merged, protocol drafted

- With the maintainer's approval, reran the Python checks (412 tests at 100% line and branch
  coverage, ruff, formatting, mypy, the three repository checks, markdownlint), folded the
  handoff into the single typed-findings commit, pushed it and opened #31 with the prepared
  description. All 16 CI checks passed; the maintainer merged it (`927c3f2`). Deleted the
  local `feat/typed-findings` branch; the remote branch is left for the maintainer.
- Drafted the study protocol on the new local branch `docs/study-protocol`: cases and strata,
  arms, reference, failure conditions with expected behaviour, measures, analysis, exclusions,
  run records and an amendment log. Checked the arm and injection details against
  `explain_decision.py`, `findings.py`, `decision.py` and `risk_scorer.py`; for example, only
  the first 100 characters of a PEP match reach the prompt, so the injection uses a corporate
  flag or typology label, and a missing transaction assessment scores 0, the same as clear.
- Brought the plan, the study data design and the research index up to date with the merge and
  the draft; the plan's minimised-input wording now matches the protocol (identifiers stay in the
  saved request, not the prompt). Merged three earlier 16 November log entries into one.
- At the maintainer's request, pushed `docs/study-protocol` and opened its pull request; it is
  not merged. No model call, deployment or paid resource.

### 16 November 2026 (earlier) — cleanup and review preparation

- Removed the temporary pause/resume reminders, then restored the reusable initialization
  prompt, which that removal had taken out too.
- Completed the final diff review of the typed-findings change (no further code change
  needed), squashed it into one commit with an identical file tree, and prepared the pull
  request description. Verified 412 Python tests at 100% line and branch coverage, ruff,
  formatting, mypy, the docs/version/asset checks and markdownlint.

### 15 November 2026 — fact-level findings and decision record

- Read the root instructions, handoff and v2 plan; verified that #30 is merged at `e10e59d`.
  The maintainer approved the additive report contract and then the implementation plan.
- Implemented canonical facts, retained evidence and a pending-review machine decision record.
  All scoring and obligation mappings use those facts; the live agents share the formulas.
  Missing/skipped assessments and individual tool fallbacks are explicit.
- Re-recorded the six demo scenarios only after asserting the approved scores and unchanged
  tiers/actions; all stand-in dimension scores also stayed unchanged. String summaries now
  include discrepancies, layering, deep chains, typologies and missing assessments.
- The independent review found two missing supporting observations: layering-only detector
  evidence and ownership nodes behind corporate flags. Regression tests first reproduced both;
  live records now retain history/detector metrics and node/jurisdiction assessments. Recorded
  demo claims remain explicitly recorded rather than inventing those observations.
- Python: 412 tests pass at 100% line and branch coverage, including actual local OCR. Mypy,
  ruff, formatting, markdownlint, docs/version checks and asset/contrast checks pass. Node.js 24:
  web lint, formatting, typecheck, 30 unit tests, build and all 30 Playwright tests pass. The final
  browser run exited successfully in 14.7 seconds against the final-code local API with explicitly
  managed local servers; earlier incomplete/timed-out attempts were not counted as passes.
- Stopped the local API and web test servers. No model study, GitHub mutation or deployment
  occurred.

### 14 November 2026 (later) — last alert, merged branches

- The maintainer merged #29; deleted `feat/synthetic-stand-ins` locally and on GitHub.
- Removed the `shadcn` command-line package, the only path to the unfixable deepmerge advisory:
  its stylesheet is copied byte-for-byte into `web/src/app/shadcn.css` with its MIT notice and
  kept out of Prettier, and the minimatch override for ts-morph went with it. 163 packages
  left the lockfile and none changed version. Checks are in that pull request.

### 14 November 2026 — security refresh, root handoff and stand-ins

- Pushed the security refresh and the documentation branch and opened #27 and #28; the
  maintainer merged both on 13 November. The documentation branch was first split into four
  commits that each pass `check_docs.py` (research drafts, the community-package removal with
  its README link, the root handoff, the plan and docs alignment) and rebased on the security
  branch so its CI ran on fixed dependencies. Merging and dismissing the deepmerge alert were
  refused by the agent's permission rules and left to the maintainer.
- Built the stand-in branch (#29) in two commits: the stand-ins with the data rule, then the
  removal of the public adverse-media file and the boost. The stand-ins' facts were chosen so
  that each agent score follows the live formulas; their tiers (HIGH, MEDIUM, LOW) are what the
  rules give. All six demo cases are now invented, so the web UI lost its "public record"
  label and the demo-only filter, and demo-only mode accepts all six. The fixture was
  re-recorded by a script that first asserted the other three scenarios were unchanged.
- Deleted the merged branches (`deps/security-refresh`, `docs/root-handoff`) locally and on
  GitHub, at the maintainer's request.
- Updated this file on #29 after the Codex review pointed out that it still described the
  migration as pending.
- The maintainer chose fact-level findings, accepting the resulting recorded score changes.

### 13 November 2026 — security advisories, data-rule answers

- Found why both Dependabot pull requests fail: advisories published since 15 October in
  `main`'s own locked packages (95 open alerts, including critical ones in Next.js and certifi),
  so CI's dependency audit fails on any pull request, not only theirs.
- Built `deps/security-refresh` from `main` in a separate worktree, so the uncommitted
  documentation was untouched: one commit for the Python lock, one for the web packages, each
  with its changelog entry. Only the flagged packages moved (plus shadcn, whose new release
  drops zod 3 and an MCP server stack, and `eslint-config-next`, aligned with Next.js). Checks
  are listed under "Current state". Committed locally; nothing pushed, as the maintainer asked.
- The installed Node.js is a v27 alpha, on which the web unit tests fail even on `main`; the web
  checks ran on a portable Node.js 24 and the lockfile was regenerated with its npm 11.
- The maintainer accepted the data-rule proposal as written (section 5 of the proposal records
  the answers); the three stand-in names have no GLEIF match. Status lines in the proposal, the
  study data design, the research index and the plan now say so.
- At the maintainer's request, removed every mention of the author's other projects from the
  plan (its "Relation to earlier work" section) and from `docs/roadmap/durable-execution.md`
  (named borrowings, a comparison table and three links); that page now states the same
  recommendations without them.
- Nothing was pushed, merged, deployed or provisioned; `docs/root-handoff` is still
  uncommitted.

### 11 November 2026 — root handoff and v2 plan alignment

- Moved the handoff to this tracked root file. `scripts/ci/check_docs.py` no longer refuses a
  tracked `HANDOFF.md` and Markdown lint now covers it; `.local/` and `.tmp/` stay untracked.
  `AGENTS.md`, `CLAUDE.md` and the Copilot instructions give the same read order.
- Revised `docs/ARGUS-V2-PLAN.md` around the matched explanation study and rechecked its
  "Starting evidence" section against the code.
- Checks on the final state: 377 tests passed with 100% line and branch coverage (381 before the
  unused package's four tests were removed); ruff, format, mypy,
  `check_docs.py`, `check_versions.py --check`, `render_assets.py --check` and markdownlint
  passed. The web UI checks (npm) were not run; no web file changed.
- The local virtual environment was rebuilt from `uv.lock` (`uv sync --frozen`) after the
  machine's Python moved from 3.14.7 to 3.14.10. `uv.lock` is unchanged.
- Moved the working drafts out of the private folder into `docs/research/` (data-rule proposal,
  study data design, related work, monitoring sources) and `docs/roadmap/durable-execution.md`,
  each marked with its status and date. Decisions and open items moved into this file.
  `.local/` now holds one file of account and machine notes; superseded private files were
  archived outside the repository with SHA-256 sums.
- Audited every tracked Markdown file outside the frozen archive against the code and against
  each other. Corrected stale dates and status lines (README, ARCHITECTURE, RELEASING,
  CONTRIBUTING, AGENTS), an unmeasured claim that explanations keep their findings, and the
  roadmap pages that contradicted the code, the data rule or the plan (plain-language
  explanation, community edition, accessibility, open knowledge graph, multimodal, witness).
  Shortened the plan's integration sections.
- Updated the target-runtime diagram's labels to the revised plan (the explanation study in
  place of the plain-language explanation; the two integrations marked as after the study)
  and regenerated its variants.
- Removed the unused `argus.community` package, its test and the Compose sketch. Nothing
  imported them. This is the only code change of the day.
- Nothing was committed, pushed, deployed or provisioned.

### 27 September – 16 October 2026 — pre-v2 cleanup (summary)

- Hackathon material archived; CI quality gate, release and dependency-refresh automation added;
  version reset to 0.1.0.
- Runtime rebuilt as one process on Microsoft Agent Framework with a data plane (local and
  Azure), one container image, and the Next.js web UI replacing Gradio.
- Deployment workflow, Bicep template, demo-only mode and 24-hour report expiry merged; nothing
  deployed.
- Attribution check added; SonarCloud findings fixed or accepted; Dependabot security updates
  merged on 15 October.
