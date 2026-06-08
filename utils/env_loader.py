"""Minimal .env loader that does not require python-dotenv.

It walks upward from the provided start path (or the current working directory)
until it finds a .env file, then loads simple KEY=VALUE pairs into os.environ.
"""
from __future__ import annotations

import os
from pathlib import Path


def load_repo_env(start: str | Path | None = None) -> None:
    base = Path(start or Path.cwd()).resolve()
    if base.is_file():
        base = base.parent

    env_path = None
    for candidate in [base, *base.parents]:
        candidate_path = candidate / ".env"
        if candidate_path.exists():
            env_path = candidate_path
            break

    if env_path is None:
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())