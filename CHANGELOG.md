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

- **ARGUS is an installable package in the standard src layout.** The application
  (`agents/`, `api/`, `ui/`, `utils/`, `accessibility/`, `community/`, `config.py`) moved to
  `src/argus/` and installs in editable mode with `uv sync`; imports are `argus.*`. Services
  start as `uv run uvicorn argus.api.main:app` and `uv run python -m argus.ui.gradio_app`.
  Checked: `uv build` produces a wheel, all 50 moves are recorded as git renames, and the suite
  passes unchanged at 100% coverage.
- **The repository root went from 16 directories to 8.** Scripts are sorted by role
  (`scripts/dev/`, `scripts/ci/`), the Foundry IQ setup moved to `infra/foundry_iq/`, and the
  roadmap to `docs/roadmap/`.
- **Tests are organised by subject.** The catch-all `test_coverage_boost.py`, `test_tools.py`
  and `test_agents.py` were split into the per-area files; three tests that mixed several
  modules became eight single-subject tests.
- **The Gradio UI shows the new logo** (`assets/brand/logo-light.svg`).
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
- **`requirements.txt`, `.coveragerc` and `python-tests.yml`**, replaced by `pyproject.toml`,
  `uv.lock` and `ci.yml`.
- **Generated files are no longer tracked:** `coverage.xml` and `data/reports_batch.jsonl`.

### Known issues

- **Foundry IQ queries never reach Foundry IQ.** `regulations_rag`, `sanctions_checker` and
  `adverse_media_scanner` call `AIProjectClient.knowledge_bases.query`, which does not exist in
  `azure-ai-projects` 1.0.0 or 2.6.1 (checked 2026-09-26). Every call falls back to mock results.
- **OCR never reaches Document Intelligence.** `ocr_processor` imports `azure.ai.formrecognizer`,
  which is not a project dependency, so every call returns mock fields.
