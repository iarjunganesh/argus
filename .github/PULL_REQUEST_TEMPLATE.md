<!-- Rules and commands: AGENTS.md. Synthetic data only. -->
<!-- markdownlint-disable-file MD041 -->

## What this changes

## How it was checked

- [ ] `uv run ruff check .` and `uv run ruff format --check .`
- [ ] `uv run mypy`
- [ ] `uv run pytest --cov` (100% line and branch coverage)
- [ ] `uv run python scripts/ci/check_docs.py`, `uv run python scripts/ci/check_versions.py --check`
      and `uv run python scripts/ci/render_assets.py --check`
- [ ] If `web/` changed: `npm --prefix web run lint`, `format:check`, `typecheck`, `test`, `build`
      and `test:e2e`

## Also

- [ ] `CHANGELOG.md` `[Unreleased]` says what became true and how it was checked
- [ ] README, `docs/` and the diagrams still match the code
