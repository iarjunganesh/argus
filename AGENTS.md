# AGENTS.md

Instructions for coding agents (Claude Code, Codex, GitHub Copilot) and for humans working on
ARGUS. This file is canonical: `CLAUDE.md` and `.github/copilot-instructions.md` only point here,
and [`CONTRIBUTING.md`](CONTRIBUTING.md) is its short version for first-time contributors.

Read [`HANDOFF.md`](HANDOFF.md) next for the current state and the next step, then
[`docs/ARGUS-V2-PLAN.md`](docs/ARGUS-V2-PLAN.md) for the study that the work leads to.

## What ARGUS is

ARGUS is a multi-agent KYC (know-your-customer) risk screening system: a FastAPI API in Python
that runs five agents as one in-process Microsoft Agent Framework workflow, and a Next.js web UI. Fixed
rules compute the risk score and tier; a language model only writes the explanation. It won a Hack
for Good award in the Microsoft Agents League 2026. The next piece of work is the matched
explanation study in [`docs/ARGUS-V2-PLAN.md`](docs/ARGUS-V2-PLAN.md) and the two changes that
plan lists before its first week.

Every tool reads through a data plane with a local implementation (synthetic data, the default,
no cloud account) and an Azure one that is not yet verified against live services, and every
result records where it came from (see "Known issues" in [`CHANGELOG.md`](CHANGELOG.md)).
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) describes the runtime as it is, not as planned.
The dated current state is in [`HANDOFF.md`](HANDOFF.md), not here.

## Rules that must not be broken

- **Every case is synthetic.** Customers, assessment cases, transactions, finances and
  identity documents are generated. Never turn a real person or company into one, give a
  generated record a real one's name, or invent a link (ownership, payment, control) between a
  generated record and a real person or company.
- **Official reference data only as published.** Entries from official sanctions and country
  lists, and public legal-entity records (for example GLEIF), may be added unmodified and
  attributed to their source, once that source's reuse terms and personal-data basis are
  recorded in [`docs/DATA-SOURCES.md`](docs/DATA-SOURCES.md). Legal entities only: list
  entries for natural persons, PEP data and company officers each need their own reviewed
  decision first. Raw downloads stay out of the repository, and ARGUS's results about a real
  company are published only in aggregate.
- **No real decisions and no effectiveness claims.** ARGUS makes recommendations for a human
  reviewer. Don't write that it improves real-world screening outcomes.
- **Explanations keep the facts.** Any change to explanation output must preserve the findings,
  the evidence references, the uncertainty and the human-review status.
- **Docs match the code.** README, `docs/` and the architecture diagrams describe what the code
  does today. If a change alters a port, fallback, weight, threshold or status, update them in
  the same pull request. Planned work is labelled as planned.
- **No paid resources without approval.** Don't create Azure, Vercel or other billable resources
  unless the maintainer explicitly approves it in the current session.
- **Nothing reaches GitHub without a go-ahead.** Pushing, opening or merging pull requests,
  tagging, releasing, and changing repository settings each need the maintainer's explicit OK in
  the current session.
- **Don't name inspirations.** Don't name or link external projects that served only as style
  references, in any file, commit message or image.
- **No AI attribution.** Commits, pull request descriptions and review replies credit no AI
  assistant: no `Co-authored-by` trailer naming one and no "Generated with" footer. Turn off any
  tool default that adds them; the Attribution workflow fails a pull request that has one.

## Secrets

- Never print, log or commit `.env`, API keys, tokens or connection strings.
- When inspecting Azure resources, query the one field you need. Never paste the output of broad
  commands such as `az ... show` or `az ... list` without a `--query`.
- If a secret leaks anywhere (terminal output, a commit, a log), say so immediately and name what
  must be rotated.

## Commands

Every command runs the same in PowerShell, bash and CI. `make` wraps them on macOS and Linux but
is not needed.

```sh
uv sync                                               # install the locked environment
uv run ruff check .                                   # lint
uv run ruff format --check .                          # formatting
uv run mypy
uv run pytest --cov                                   # tests, 100% line + branch coverage required
uv run python scripts/ci/check_docs.py                   # docs agree with the repository
uv run python scripts/ci/check_versions.py --check        # version pins agree (offline)
uv run python scripts/ci/render_assets.py --check        # image variants current, WCAG AA contrast

npm ci --prefix web                                   # the web UI (Node.js 24): locked packages
npm --prefix web run lint
npm --prefix web run format:check
npm --prefix web run typecheck
npm --prefix web test                                 # unit tests
npm --prefix web run build
npm --prefix web run test:e2e                         # Playwright; needs the API (web/README.md)
```

`uv run python scripts/ci/render_assets.py` regenerates the image variants and PNG/GIF exports after
you edit an SVG master (see [`assets/README.md`](assets/README.md)).

Tests need no cloud credentials: `tests/conftest.py` ignores `.env`, removes cloud and ARGUS
settings, and points the local data plane at `tests/fixtures/data/`. On Windows, if pytest fails with a
`PermissionError` on its temporary directory, add `--basetemp` pointing at any writable folder.

## Definition of done

A change is done when:

1. All the commands above pass. Coverage stays at 100%: new code arrives with its tests, and a
   line that truly can't be tested gets an explicit, commented exclusion rather than a lower
   floor.
2. `CHANGELOG.md` has an `[Unreleased]` entry that says **what became true and how it was
   checked**, not which files moved.
3. A renamed or moved file is followed by a search of the whole repository for its old path, in
   the same commit.
4. Commits stay small and green: moves separate from edits, formatting separate from logic.

## Dependencies after every release

After each release tag, every dependency moves to its latest version in a pull request titled
`deps: refresh after vX.Y.Z`: the Python packages in `uv.lock` and the `pyproject.toml`
minimums, the GitHub Actions pins, and the Python version once all dependencies support it.
Microsoft Agent Framework is pinned exactly, and its compatibility is part of that check. **A
release isn't finished until that pull request exists**; report which packages moved and whether
anything broke. `release.yml` opens that pull request automatically after each tag (see
[`docs/RELEASING.md`](docs/RELEASING.md)); to do the same by hand:

```sh
uv lock --upgrade && uv sync
```

then run every command above.

## Repository map

| Path | What it holds |
| --- | --- |
| `src/` | The application: the installable package `argus` (see below) |
| `web/` | The web UI: Next.js, TypeScript and shadcn/ui, with unit and Playwright tests |
| `data/` | Synthetic data generators and public-source demo data |
| `infra/` | The Azure deployment: Bicep template, `populate.py` and `teardown.py`, and `foundry_iq/` (create and fill the knowledge bases) |
| `tests/` | The test suite (hermetic; no cloud access) |
| `scripts/` | `dev/`: demo launchers and local helpers. `ci/`: the docs, version and release checks, the dependency refresh, and the image renderer |
| `assets/` | Brand and architecture images, each drawn from an SVG master |
| `docs/` | Architecture as it runs today, the v2 plan, `research/` (working drafts and dated notes behind the study) and `roadmap/` (ideas not yet scheduled) |
| `archive/` | Frozen hackathon material. Never edit it except to add to its index. |

Inside `src/argus/`:

| Package | What it holds |
| --- | --- |
| `agents/` | The orchestrator (the Agent Framework workflow) and the five agents, each with its `tools/` |
| `api/` | The FastAPI API (submit, status, report, progress stream) and its request schemas |
| `data_plane/` | The four data interfaces (retriever, entity store, report store, OCR), each with a local and an Azure implementation |
| `utils/` | Shared helpers: `.env` loader, JSON logger, the six recorded demo profiles |
| `accessibility/` | WCAG contrast utilities, also used to check the images |
| `models.py` | The one language-model client factory (`ARGUS_MODEL_PROVIDER`) |
| `config.py` | The Azure client factories behind the Azure data plane |

`scripts/ci/check_docs.py` fails if a tracked top-level directory is missing from this table, or if
the table lists one that doesn't exist.

## Shared state and private material

- [`HANDOFF.md`](HANDOFF.md) at the repository root is the shared record for every tool and
  person: current state, next step and a session log. Conversation history does not move
  between tools, so before you stop, update its "Current state" and "Next step" sections and
  add a session-log entry.
- `HANDOFF.md` is tracked and public. Write only public-safe project state in it: no account,
  subscription or billing details, no personal correspondence, no unpublished drafts.
- Drafts, proposals and research notes go in [`docs/research/`](docs/research/README.md), each
  with a status line and a date. Decisions and open items go in `HANDOFF.md`.
- `.local/` is the ignored home for what cannot be published: account, subscription and billing
  notes, notes about one machine, and private measurement records. Keep it small. It is
  durable: never delete or clear it without the maintainer asking, and never commit it. Cloud
  agents that work from a copy of the GitHub repository cannot see it.
- `.tmp/` is disposable scratch that anyone may empty; don't keep anything there that must
  survive.
- `check_docs.py` fails if anything under `.local/` or `.tmp/` is tracked.
