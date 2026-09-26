# Contributing to ARGUS

Thanks for your interest. ARGUS is being cleaned up before the v2 work described in
[`docs/ARGUS-V2-PLAN.md`](docs/ARGUS-V2-PLAN.md), so the structure may still move. Issues and
small, focused pull requests are welcome.

[`AGENTS.md`](AGENTS.md) is the rulebook for humans and coding agents alike: the rules that must
not be broken, the commands, the definition of done and a map of the repository. This page is
the short version.

## Set up

Install [uv](https://docs.astral.sh/uv/). It installs the pinned Python version and the locked
dependencies, and it installs ARGUS itself as the editable package `argus` from `src/`.

```sh
git clone https://github.com/iarjunganesh/argus.git
cd argus
uv sync
```

No cloud account is needed: without credentials every external call falls back to mock data.

## Before you open a pull request

Run the same checks as CI:

```sh
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest --cov
uv run python scripts/ci/check_docs.py
uv run python scripts/ci/check_versions.py --check
uv run python scripts/ci/render_assets.py --check
```

- **Tests come with the code.** Coverage is 100% of lines and branches, and CI enforces it.
- **Add a `CHANGELOG.md` entry** under `[Unreleased]` that says what became true and how you
  checked it.
- **Keep the docs true.** If you change a port, a fallback, a scoring weight or a threshold,
  update the README, `docs/` and the diagrams in `assets/` in the same pull request.
- **Synthetic data only.** Never add real people's or companies' personal data, in code, tests
  or issues.

## What helps most right now

1. Accessibility beyond the tested risk palette: screen-reader announcements and keyboard
   navigation (see [`docs/roadmap/accessibility.md`](docs/roadmap/accessibility.md)).
2. Translations of explanation output: the people who most need plain language often don't
   read English.

## Security issues

Please don't open a public issue for a vulnerability. See [`SECURITY.md`](SECURITY.md).

## Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
