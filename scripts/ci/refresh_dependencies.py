"""Prepare dependency changes and a review report, preserving failed checks as evidence."""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def commands(python: str) -> list[tuple[str, list[str]]]:
    return [
        (
            "Upstream before refresh",
            [
                python,
                "scripts/ci/check_versions.py",
                "--check-upstream",
                "--report",
                ".tmp/upstream-before.md",
            ],
        ),
        ("Upgrade lock", ["uv", "lock", "--upgrade"]),
        ("Raise minimums", [python, "scripts/ci/check_versions.py", "--write-minimums"]),
        ("Relock minimums", ["uv", "lock"]),
        (
            "Refresh action pins and inventory",
            [
                python,
                "scripts/ci/check_versions.py",
                "--write",
                "--report",
                ".tmp/upstream-after.md",
                "--candidate-file",
                ".tmp/python-candidate.txt",
            ],
        ),
        ("Synchronize", ["uv", "sync", "--locked"]),
        ("Lint", ["uv", "run", "--locked", "ruff", "check", "."]),
        ("Format", ["uv", "run", "--locked", "ruff", "format", "--check", "."]),
        ("Types", ["uv", "run", "--locked", "mypy"]),
        ("Tests", ["uv", "run", "--locked", "pytest", "--cov"]),
        ("Docs", ["uv", "run", "--locked", "python", "scripts/ci/check_docs.py"]),
        ("Versions", [python, "scripts/ci/check_versions.py", "--check"]),
        ("Assets", ["uv", "run", "--locked", "python", "scripts/ci/render_assets.py", "--check"]),
        (
            "Audit export",
            [
                "uv",
                "export",
                "--locked",
                "--all-groups",
                "--no-emit-project",
                "--format",
                "requirements.txt",
                "--output-file",
                ".tmp/audit.txt",
            ],
        ),
        (
            "Audit",
            ["uvx", "pip-audit", "--strict", "--requirement", ".tmp/audit.txt", "--disable-pip"],
        ),
    ]


def run(root: Path, tag: str, steps: list[tuple[str, list[str]]]) -> int:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.[1-9]\d*)?", tag):
        raise ValueError("Invalid release tag")
    scratch = root / ".tmp"
    scratch.mkdir(exist_ok=True)
    # A failed repeat must never re-use an earlier inventory or candidate.
    for name in ["upstream-before.md", "upstream-after.md", "python-candidate.txt", "audit.txt"]:
        (scratch / name).unlink(missing_ok=True)
    env = {**os.environ, "PYTHONUTF8": "1"}
    env.pop("UV_LOCKED", None)
    results = []
    for label, command in steps:
        print(f"::group::{label}", flush=True)
        try:
            code = subprocess.run(command, cwd=root, env=env, timeout=900, check=False).returncode
        except OSError, subprocess.TimeoutExpired:
            code = 1
        results.append((label, code))
        print(f"::endgroup::\n{label}: {'PASS' if code == 0 else 'FAIL'}", flush=True)
    body = [
        "# Dependency refresh",
        "",
        f"Refresh after `{tag}`.",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    body += [f"| {label} | {'PASS' if code == 0 else 'FAIL'} |" for label, code in results]
    for title, name in [
        ("Before refresh", "upstream-before.md"),
        ("After refresh", "upstream-after.md"),
    ]:
        path = scratch / name
        body += [
            "",
            f"## {title}",
            "",
            path.read_text("utf-8").strip()
            if path.exists()
            else "Inventory unavailable: see the failed step in the workflow log.",
        ]
    body += [
        "",
        "Agent Framework is not a dependency yet; its contract gate starts in Phase 5.",
        "Web and container inventories start when those surfaces exist in Phase 5.",
        "",
    ]
    (root / "docs/DEPENDENCY-REFRESH.md").write_text("\n".join(body), encoding="utf-8")
    return int(any(code for _, code in results))


if __name__ == "__main__":
    sys.exit(run(ROOT, sys.argv[1], commands(sys.executable)))
