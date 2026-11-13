# ARGUS handoff

Read [AGENTS.md](AGENTS.md), this file, then the [v2 plan](docs/ARGUS-V2-PLAN.md). Update Current
state, Next step and Session log before stopping.

This file is tracked and public. It holds project state only. Drafts and research notes are in
[`docs/research/`](docs/research/README.md). Only account, billing and machine notes stay in
the ignored `.local/` folder.

Resume prompt (paste into any agent, with this repository open):

```text
Read AGENTS.md and HANDOFF.md, then docs/ARGUS-V2-PLAN.md, and continue from Next step. Before stopping, update Current state and Next step in HANDOFF.md and add a Session log entry.
```

Claude Code reads `CLAUDE.md`, Copilot reads `.github/copilot-instructions.md`, and Codex reads
`AGENTS.md`; all three point here. Conversation history does not move between tools or sessions.

## Current state — 14 November 2026

- **Source.** `main` is at `056e526`. On 13 November the maintainer merged #27 (security
  refresh) and #28 (root handoff, research drafts, revised plan); CI passed on `main` after
  #27. Dependabot closed #25 and #26 as superseded. The merged branches were deleted locally
  and on GitHub.
- **Security alerts.** One Dependabot alert is open: deepmerge 4.3.1 (low), used only by the
  shadcn command-line tool, with no fixed release. Dismissing it needs the maintainer in the
  GitHub UI (an agent's attempt was refused by its permission rules).
- **Stand-ins and data rule: pull request #29, open, CI green.** Synthetic Payments AG (HIGH,
  56.5), Synthetic Nordic Bank A/S (MEDIUM, 36.0) and Synthetic Pacific Banking Corporation
  (LOW, 18.2) replace the three real-company profiles. Their profile scores are what the live
  agents compute from their facts (a test recomputes them). All six demo cases are invented, so
  demo-only mode accepts all six. `AGENTS.md` carries the accepted data rule, with an empty
  `docs/DATA-SOURCES.md`. The public adverse-media file and the 12-point adverse-media boost are
  removed. The other three scenarios' recorded outcomes did not move.
- **What runs.** One process: a FastAPI API that runs five agents as a Microsoft Agent Framework
  workflow, and a Next.js web UI. Fixed rules compute the score and tier; a language model only
  writes the explanation. The default is the local data plane with synthetic data and no cloud
  account. The Azure data plane exists but is not verified against live services.
- **Not released, not deployed.** `pyproject.toml` says 0.1.0, but there is no tag and no GitHub
  Release. The deployment workflow and Bicep template are merged; no Azure or Vercel resource has
  been created.
- **v2 plan revised on 11 November.** The study leads with a matched comparison: the same
  rule-determined findings explained from raw and from minimised input, then injection and
  missing-step conditions. Simplifying the wording is the follow-up question.
- **What the study still needs from the code:** typed findings. `key_findings` are free-text
  strings that can carry names and do not record everything that sets the score (identity
  confidence, layering, typology hits and ownership depth move the score without appearing).
  The customer-facing explanation variant is tested but not wired in.
- **Checks on 14 November, on #29's branch:** 380 tests at 100% line and branch coverage (also
  at its first commit alone), ruff, format, mypy, the three repository checks and markdownlint
  pass; with Node.js 24 the web lint, format, typecheck, unit tests, build and the 30 Playwright
  tests against a local API pass. CI passed on the pull request.

## Next step

Maintainer decisions that block work:

1. Merge #29 (or ask for changes).
2. Dismiss the deepmerge alert in the GitHub UI as a tolerable risk (development-only tool, no
   fixed release), or ask for the alternative: drop the `shadcn` package and copy its stylesheet.
3. Typed findings, one design choice (see below).
4. Whether `v0.1.0` still waits for a first Azure deployment and an observed idle-day cost (the
   original cleanup exit gate), or is tagged first because the study does not need hosting.
5. A model budget for the study, and which model configuration is pinned.

Then, in order:

1. Typed findings as the only inputs to scoring (one pull request, with the demo scenarios'
   tiers unchanged). Design: "Shared rule and decision record" in
   [`docs/research/study-data-design.md`](docs/research/study-data-design.md).
2. v2 Week 1: write and commit the study protocol, then capture the baseline.

**The typed-findings choice.** The design asks for fact-level findings (each discrepancy,
screening hit, high-risk ownership node, deep ownership chain, structuring and layering flag and
typology hit as its own record), with the agent scores computed from them by the live formulas.
Live runs then score exactly as today. The three original recorded profiles (Jane Synthetic,
Synthetic Holdings B.V., Cayman Synth Capital) carry hand-set scores that those formulas do not
reproduce, so their scores would move while their tiers stay: about 5.8 → 3.0 (LOW), 49.5 → 44
(MEDIUM) and 73.5 → 76 (CRITICAL, held by the sanctions match either way). The alternative keeps
every score by recording each agent's score as a finding of its own, which is exact but coarser
for the study's subset analysis. Either way a dimension whose agent did not run keeps today's
default and is recorded as not assessed, not as clear.

Nothing is pushed, tagged, deployed or paid for without the maintainer's go-ahead in the session.

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
- 13 November 2026: the data-rule wording is accepted as written, the empty
  `docs/DATA-SOURCES.md` register is added with it, and the stand-ins are Synthetic Payments AG,
  Synthetic Nordic Bank A/S and Synthetic Pacific Banking Corporation (all on the stand-in
  branch). One security-refresh pull request replaces Dependabot's #25 and #26. ARGUS files name
  none of the author's other projects, not even as cited earlier work.

## Open items

- **Deployment, when approved.** Steps are in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md): approve
  the resources it lists, set up the workflow identity and the GitHub `azure` environment, deploy,
  fill the data plane, run the smoke check with its cold-start time, confirm zero replicas after
  30 idle minutes and observe one idle day's cost. Then the Vercel project (root `web`, variables
  `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_ARGUS_DEMO_ONLY=true`). When live, update the README
  hosting badges, the ARCHITECTURE hosting heading and the CHANGELOG known issue.
- CodeQL alert #1 (Faker `tax_id`) is a false positive, to dismiss in the GitHub UI.
- `eslint-config-next` matches Next.js (16.4.6) on `main`. ESLint 9 and
  TypeScript 6.0 are held back by peer limits. Remove the minimatch `overrides` entry in
  `web/package.json` once typescript-eslint and ts-morph depend on minimatch 11. Move `web/.nvmrc` and `@types/node` by hand when
  Node 26 is the LTS.
- Undecided: add a `documents` field to the API, or keep "the API takes no documents" as a
  known issue for `v0.1.0`.

## Session log

Newest first. Keep about ten entries; older history is in `CHANGELOG.md` and the merged pull
requests.

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
- Did not start typed findings: the choice above changes recorded scores, so it is the
  maintainer's.

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
