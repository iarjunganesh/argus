"""Validate a release tag against package metadata and extract its changelog section."""

import argparse
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(alpha|beta|rc)\.[1-9]\d*)?")


def extract(root: Path, tag: str) -> str:
    if not TAG.fullmatch(tag):
        raise ValueError("Expected vX.Y.Z or vX.Y.Z-(alpha|beta|rc).N")
    version = tag[1:]
    project = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]
    # PEP 440 spells SemVer rc.1 as rc1 (and alpha/beta as a/b).
    package_version = re.sub(
        r"-(alpha|beta|rc)\.", lambda m: {"alpha": "a", "beta": "b", "rc": "rc"}[m[1]], version
    )
    if project["version"] != package_version:
        raise ValueError(f"Tag {tag} disagrees with project version {project['version']}")
    text = (root / "CHANGELOG.md").read_text("utf-8")
    sections = re.split(r"^## \[([^\]]+)\][^\n]*\n", text, flags=re.MULTILINE)
    matches = [
        sections[i + 1].strip() for i in range(1, len(sections), 2) if sections[i] == version
    ]
    if len(matches) != 1 or not matches[0]:
        raise ValueError(f"Expected one nonempty CHANGELOG.md section for [{version}]")
    return matches[0] + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        notes = extract(ROOT, args.tag)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(notes, encoding="utf-8")


if __name__ == "__main__":
    main()
