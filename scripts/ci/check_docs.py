"""Check that the documentation agrees with the repository.

Run from the repository root:

    uv run python scripts/ci/check_docs.py

Each check guards against a kind of drift that has already happened in this project:
links left pointing at moved files, a README advertising a Python version CI doesn't use,
unfinished markers shipped in public docs, a repository map that no longer matches the tree,
and local working notes committed by accident.
Exits non-zero and prints every problem found.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Frozen hackathon material is kept as submitted, so its links and wording are not checked.
SKIP_PREFIXES = ("archive/",)

# Public documents that must not ship with unfinished markers.
PUBLIC_DOCS = ("README.md", "CHANGELOG.md", "docs/")
UNFINISHED = re.compile(r"\b(TBD|FIXME|XXX)\b|lorem ipsum|\[to fill\]", re.IGNORECASE)

# Local working files that must never be tracked.
NEVER_TRACKED_FILES = ("HANDOFF.md", ".env", ".claude/settings.local.json")
NEVER_TRACKED_DIRS = (".tmp/",)

LINK = re.compile(r"\]\(([^)\s]+)\)")
MAP_ROW = re.compile(r"^\| `([^`/]+)/` \|", re.MULTILINE)


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    return [line for line in out.splitlines() if line]


def check_links(markdown: list[str]) -> list[str]:
    problems = []
    for rel in markdown:
        path = ROOT / rel
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for target in LINK.findall(line):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                file_part = target.split("#", 1)[0]
                if not (path.parent / file_part).resolve().exists():
                    problems.append(f"{rel}:{number}: broken link to {target}")
    return problems


def check_unfinished(markdown: list[str]) -> list[str]:
    problems = []
    for rel in markdown:
        if not rel.startswith(PUBLIC_DOCS):
            continue
        for number, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            if UNFINISHED.search(line):
                problems.append(f"{rel}:{number}: unfinished marker: {line.strip()[:80]}")
    return problems


def check_python_version() -> list[str]:
    problems = []
    pinned = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requires = project["project"]["requires-python"]
    if requires != f">={pinned}":
        problems.append(f"pyproject.toml requires-python {requires!r} != '>={pinned}'")
    badge = re.search(r"badge/Python-([0-9.]+)-", (ROOT / "README.md").read_text("utf-8"))
    if not badge or badge.group(1) != pinned:
        found = badge.group(1) if badge else "none"
        problems.append(f"README Python badge shows {found}, .python-version is {pinned}")
    return problems


def check_docs_index() -> list[str]:
    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    return [
        f"docs/README.md does not list {doc.name}"
        for doc in sorted((ROOT / "docs").glob("*.md"))
        if doc.name != "README.md" and f"({doc.name})" not in index
    ]


def check_changelog() -> list[str]:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return [] if "## [Unreleased]" in text else ["CHANGELOG.md has no '## [Unreleased]' section"]


def check_repo_map(files: list[str]) -> list[str]:
    """AGENTS.md's repository map lists exactly the tracked top-level directories."""
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    # The first table under the heading lists the top level; later tables go deeper.
    section = text.split("## Repository map", 1)[-1].lstrip("\n")
    table = section.split("\n\n", 1)[0]
    listed = set(MAP_ROW.findall(table))
    tracked = {f.split("/", 1)[0] for f in files if "/" in f and not f.startswith(".")}
    return [f"AGENTS.md repository map is missing {name}/" for name in sorted(tracked - listed)] + [
        f"AGENTS.md repository map lists {name}/, which is not tracked"
        for name in sorted(listed - tracked)
    ]


def check_never_tracked(files: list[str]) -> list[str]:
    return [
        f"{name} must not be tracked"
        for name in files
        if name in NEVER_TRACKED_FILES or name.startswith(NEVER_TRACKED_DIRS)
    ]


def main() -> int:
    files = tracked_files()
    markdown = [f for f in files if f.endswith(".md") and not f.startswith(SKIP_PREFIXES)]
    problems = [
        *check_links(markdown),
        *check_unfinished(markdown),
        *check_python_version(),
        *check_docs_index(),
        *check_changelog(),
        *check_repo_map(files),
        *check_never_tracked(files),
    ]
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        print(f"{len(problems)} documentation problem(s).")
        return 1
    print(f"Documentation checks passed ({len(markdown)} Markdown files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
