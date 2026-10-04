"""Check that no commit message or pull request description credits an AI assistant.

Run from the repository root:

    python scripts/ci/check_attribution.py [BASE [HEAD]]

Checks the messages of the commits in BASE..HEAD (default: origin/main..HEAD) and, when run for a
GitHub pull request, its description (from the event in GITHUB_EVENT_PATH). Commits and pull
requests here are the maintainer's own (AGENTS.md); some assistants add a co-author trailer or a
"Generated with" footer by default, and this catches it before it reaches main. Exits non-zero
and prints each line found. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ASSISTANTS = r"claude|anthropic|copilot|codex|openai|chatgpt|gemini"
ATTRIBUTION = re.compile(
    rf"^\s*co-authored-by:.*\b({ASSISTANTS})\b"  # a co-author trailer naming an assistant
    rf"|generated (with|by) \W*\[?\s*({ASSISTANTS})"  # a "Generated with ..." footer
    r"|noreply@anthropic\.com",
    re.IGNORECASE | re.MULTILINE,
)


def attributions(text: str) -> list[str]:
    """The lines of `text` that credit an AI assistant."""
    return [line.strip() for line in text.splitlines() if ATTRIBUTION.search(line)]


def commit_messages(base: str, head: str) -> dict[str, str]:
    """Each commit in base..head, by short hash, with its full message."""
    out = subprocess.run(  # noqa: S603 - fixed program; the range comes from CI or the caller
        ["git", "log", "--format=%h%x00%B%x01", f"{base}..{head}"],  # noqa: S607 - git on PATH
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    entries = (entry.strip("\n").split("\0", 1) for entry in out.split("\1") if entry.strip())
    return {sha: message for sha, message in entries}


def pull_request_body(event_path: str | None) -> str | None:
    """The pull request's description, when GitHub ran this for a pull request event."""
    if not event_path:
        return None
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pull_request = event.get("pull_request")
    return (pull_request.get("body") or "") if pull_request else None


def problems(base: str, head: str, event_path: str | None) -> list[str]:
    found = [
        f"commit {sha}: {line}"
        for sha, message in commit_messages(base, head).items()
        for line in attributions(message)
    ]
    body = pull_request_body(event_path)
    if body is not None:
        found += [f"pull request description: {line}" for line in attributions(body)]
    return found


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    base = args[0] if args else "origin/main"
    head = args[1] if len(args) > 1 else "HEAD"
    found = problems(base, head, os.environ.get("GITHUB_EVENT_PATH"))
    for problem in found:
        print(problem)
    if found:
        print("\nRemove these lines: commits and pull requests here credit no AI assistant.")
        return 1
    print(f"No AI attribution in {base}..{head}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
