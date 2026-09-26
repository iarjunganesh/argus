# AGENTS.md

Instructions for coding agents (Claude Code, Codex, GitHub Copilot) and for humans working on
ARGUS. This file is canonical: `CLAUDE.md` and `.github/copilot-instructions.md` only point here.

## What ARGUS is

ARGUS is a multi-agent KYC (know-your-customer) risk screening system in Python: five FastAPI
agent services, an orchestrator, a FastAPI gateway and a Gradio UI. Fixed rules compute the risk
score and tier; a language model only writes the explanation. It won a Hack for Good award in the
Microsoft Agents League 2026 and is now being cleaned up before the v2 work in
[`docs/ARGUS-V2-PLAN.md`](docs/ARGUS-V2-PLAN.md).

State as of 2026-09-26: Foundry IQ queries and OCR return mock data on every run (see the
"Known issues" in [`CHANGELOG.md`](CHANGELOG.md)). [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
describes the runtime as it is, not as planned.

## Rules that must not be broken

- **Synthetic data only.** Never add real people's or real companies' personal data. The public
  demo cases (for example Wirecard AG) use published enforcement facts only.
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
uv run python scripts/ci/render_assets.py --check        # image variants current, WCAG AA contrast
```

`uv run python scripts/ci/render_assets.py` regenerates the image variants and PNG/GIF exports after
you edit an SVG master (see [`assets/README.md`](assets/README.md)).

Tests need no cloud credentials: `tests/conftest.py` ignores `.env` and removes Azure credentials,
so every external client falls back to mock data. On Windows, if pytest fails with a
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
Microsoft Agent Framework compatibility is part of that check once it is a dependency. **A
release isn't finished until that pull request exists**; report which packages moved and whether
anything broke. Until the release workflow automates it, do it by hand:

```sh
uv lock --upgrade && uv sync
```

then run every command above.

## Repository map

| Path | What it holds |
| --- | --- |
| `src/` | The application: the installable package `argus` (see below) |
| `data/` | Synthetic data generators and public-source demo data |
| `infra/` | Bicep template, Azure setup scripts, and `foundry_iq/` (create and fill the knowledge bases) |
| `tests/` | The test suite (hermetic; no cloud access) |
| `scripts/` | `dev/`: demo launchers and local helpers. `ci/`: the docs check and the image renderer |
| `assets/` | Brand and architecture images, each drawn from an SVG master |
| `docs/` | Architecture as it runs today, the v2 plan, and `roadmap/` (ideas not yet scheduled) |
| `archive/` | Frozen hackathon material. Never edit it except to add to its index. |

Inside `src/argus/`:

| Package | What it holds |
| --- | --- |
| `agents/` | The orchestrator and the five agent services, each with its `tools/` |
| `api/` | The FastAPI gateway and its request/response schemas |
| `ui/` | The Gradio UI (to be replaced by a web UI in v2) |
| `utils/` | Shared helpers: `.env` loader, JSON logger, the six recorded demo profiles |
| `accessibility/` | WCAG contrast utilities, also used to check the images |
| `community/` | Community Edition configuration presets (a design, not yet runnable) |
| `config.py` | Settings and the Azure client factories |

`scripts/ci/check_docs.py` fails if a tracked top-level directory is missing from this table, or if
the table lists one that doesn't exist.

## Handoff between tools

If `HANDOFF.md` exists at the repository root, read it before doing anything else: it holds the
current state, the next step and decisions already made. Before you stop, update its "Current
state" and "Next step" sections and add a session-log entry. `HANDOFF.md` and `.tmp/` are local
working files. Never commit them; `check_docs.py` fails if they are tracked.
