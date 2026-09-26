# CLAUDE.md

@AGENTS.md

## Claude Code notes

- Everything in `AGENTS.md` applies. It is the single source; don't copy its rules here.
- `.claude/settings.json` pre-approves the read-only checks (`uv run pytest`, `ruff`, `mypy`,
  the two scripts' checks) and `git status`, `diff` and `log`. Anything that writes to GitHub
  still needs the maintainer's go-ahead.
- On this project's Windows machines both PowerShell and Git Bash are available; the commands in
  `AGENTS.md` work in either.
