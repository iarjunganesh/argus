"""Inventory the current Python/action surfaces; check offline or refresh from upstream.

Network failures are errors, never evidence that a dependency is current. Web/container
support must be added with those Phase 5 surfaces; encountering either fails closed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from functools import cache
from pathlib import Path
from urllib.request import Request, urlopen

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.tags import compatible_tags, cpython_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parents[2]
ACTION = re.compile(
    r"(?P<prefix>uses:\s+)(?P<repo>[\w.-]+/[\w.-]+)@(?P<sha>[\w.-]+)"
    r"(?:\s+#\s*(?P<tag>v[\w.-]+))?"
)
DEPENDENCY = re.compile(r'(?P<quote>["\'])(?P<req>[A-Za-z0-9][^"\'\n]*)(?P=quote)')


def read_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text("utf-8"))


def requirements(project: dict) -> list[Requirement]:
    groups = project.get("dependency-groups", {}).values()
    raw = [
        *project["project"].get("dependencies", []),
        *[item for group in groups for item in group if isinstance(item, str)],
    ]
    return [Requirement(item) for item in raw]


def packages(root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for package in read_toml(root / "uv.lock")["package"]:
        if "registry" in package.get("source", {}):
            result.setdefault(canonicalize_name(package["name"]), []).append(package["version"])
    return {name: sorted(set(versions), key=Version) for name, versions in result.items()}


def workflows(root: Path) -> list[Path]:
    return sorted((root / ".github/workflows").glob("*.y*ml"))


def check(root: Path) -> list[str]:
    project = read_toml(root / "pyproject.toml")
    locked = read_toml(root / "uv.lock")
    pinned = (root / ".python-version").read_text("utf-8").strip()
    problems = []
    for label, value in [
        ("project", project["project"]["requires-python"]),
        ("lock", locked["requires-python"]),
    ]:
        if value != f">={pinned}":
            problems.append(f"{label}: requires-python disagrees with .python-version")
    if project["tool"]["ruff"]["target-version"] != "py" + pinned.replace(".", ""):
        problems.append("Ruff target disagrees with .python-version")
    if project["tool"]["mypy"]["python_version"] != pinned:
        problems.append("Mypy target disagrees with .python-version")
    own = [p for p in locked["package"] if p["name"] == project["project"]["name"]]
    if len(own) != 1 or own[0]["version"] != project["project"]["version"]:
        problems.append("Project version disagrees with uv.lock")
    inventory = packages(root)
    for req in requirements(project):
        name = canonicalize_name(req.name)
        versions = inventory.get(name, [])
        if not versions or not all(req.specifier.contains(v, prereleases=True) for v in versions):
            problems.append(f"{name}: requirement {req.specifier} disagrees with lock {versions}")
        if name.startswith("agent-framework") and not re.fullmatch(r"==[^*,]+", str(req.specifier)):
            problems.append(f"{name}: Agent Framework requires an exact pin")
    seen: dict[str, tuple[str, str]] = {}
    for path in workflows(root):
        text = path.read_text("utf-8")
        for match in ACTION.finditer(text):
            repo, sha, tag = match["repo"], match["sha"], match["tag"]
            if not re.fullmatch(r"[0-9a-f]{40}", sha) or not tag:
                problems.append(f"{path.name}: {repo} needs a full SHA and version comment")
            pin = (sha, tag or "")
            if repo in seen and seen[repo] != pin:
                problems.append(f"{repo}: inconsistent action pins")
            seen[repo] = pin
        for value in re.findall(r"python-version:\s*['\"]?([\d.]+)", text):
            if value != pinned:
                problems.append(f"{path.name}: Python {value} disagrees with {pinned}")
    if (root / "web/package.json").exists() or (root / "Dockerfile").exists():
        problems.append("Extend the version inventory for web/container surfaces before Phase 5")
    return problems


@cache
def fetch(url: str):
    headers = {"User-Agent": "ARGUS-dependency-inventory"}
    if url.startswith("https://api.github.com/") and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def latest_package(data: dict, allow_pre: bool) -> str:
    choices = []
    for version, files in data["releases"].items():
        try:
            parsed = Version(version)
        except InvalidVersion:
            continue
        if parsed.is_devrelease or (parsed.is_prerelease and not allow_pre):
            continue
        if any(not file.get("yanked", False) for file in files):
            choices.append(parsed)
    if not choices:
        raise ValueError("No non-yanked upstream release")
    return str(max(choices))


def action_release(repo: str) -> tuple[str, str]:
    release = fetch(f"https://api.github.com/repos/{repo}/releases/latest")
    tag = release["tag_name"]
    if not re.fullmatch(r"v\d+(?:\.\d+){0,2}", tag):
        raise ValueError(f"{repo}: unsupported release tag")
    obj = fetch(f"https://api.github.com/repos/{repo}/git/ref/tags/{tag}")["object"]
    for _ in range(5):
        if obj["type"] == "commit":
            if not re.fullmatch(r"[0-9a-f]{40}", obj["sha"]):
                raise ValueError(f"{repo}: invalid commit SHA")
            return tag, obj["sha"]
        if obj["type"] != "tag":
            break
        obj = fetch(f"https://api.github.com/repos/{repo}/git/tags/{obj['sha']}")["object"]
    raise ValueError(f"{repo}: could not resolve release to a commit")


def wheel_ready(files: list[dict], minor: str) -> bool:
    version = tuple(int(part) for part in minor.split("."))
    platforms = [
        "win_amd64",
        "manylinux_2_28_x86_64",
        "manylinux_2_17_x86_64",
        "manylinux2014_x86_64",
        "linux_x86_64",
    ]
    # Require both the Windows development and Linux CI/deployment platforms.
    for platform_group in [platforms[:1], platforms[1:]]:
        supported = set(
            cpython_tags(version, abis=["cp" + minor.replace(".", "")], platforms=platform_group)
        )
        supported.update(compatible_tags(version, platforms=platform_group))
        found = False
        for file in files:
            if file.get("yanked") or not file["filename"].endswith(".whl"):
                continue
            if not SpecifierSet(file.get("requires_python") or "").contains(minor + ".0"):
                continue
            _, _, _, tags = parse_wheel_filename(file["filename"])
            if supported & tags:
                found = True
        if not found:
            return False
    return True


def upstream(root: Path) -> tuple[list[str], dict[str, tuple[str, str]], str | None]:
    inventory = packages(root)
    rows = ["| Surface | Locked | Latest | Status |", "| --- | --- | --- | --- |"]
    metadata = {}
    for name, versions in sorted(inventory.items()):
        data = fetch(f"https://pypi.org/pypi/{name}/json")
        metadata[name] = data
        allow_pre = name.startswith("agent-framework") and any(
            Version(v).is_prerelease for v in versions
        )
        latest = latest_package(data, allow_pre)
        current = min(map(Version, versions))
        status = "current"
        if Version(latest) > current:
            status = "MAJOR" if Version(latest).major > current.major else "update"
        rows.append(f"| {name} | {', '.join(versions)} | {latest} | {status} |")
    for raw in read_toml(root / "pyproject.toml").get("build-system", {}).get("requires", []):
        req = Requirement(raw)
        latest = latest_package(fetch(f"https://pypi.org/pypi/{req.name}/json"), False)
        status = "within range" if req.specifier.contains(latest) else "update build range"
        rows.append(f"| Build: {req.name} | {req.specifier} | {latest} | {status} |")
    actions = {}
    for path in workflows(root):
        for match in ACTION.finditer(path.read_text("utf-8")):
            repo = match["repo"]
            if repo in actions:
                continue
            tag, sha = action_release(repo)
            actions[repo] = tag, sha
            status = "current" if sha == match["sha"] else "update"
            if match["tag"] and Version(tag).major > Version(match["tag"]).major:
                status = "MAJOR"
            rows.append(f"| {repo} | {match['tag']} | {tag} | {status} |")
    refs = fetch("https://api.github.com/repos/python/cpython/git/matching-refs/tags/v3.")
    stable = [
        Version(ref["ref"].rsplit("/", 1)[1][1:])
        for ref in refs
        if re.fullmatch(r"refs/tags/v3\.\d+\.\d+", ref["ref"])
    ]
    latest_python = max(stable)
    candidate = f"{latest_python.major}.{latest_python.minor}"
    current_python = (root / ".python-version").read_text("utf-8").strip()
    blocked = []
    if Version(candidate) > Version(current_python):
        for name, versions in inventory.items():
            for version in versions:
                if not wheel_ready(metadata[name]["releases"][version], candidate):
                    blocked.append(f"{name}=={version}")
        state = "blocked: " + ", ".join(blocked) if blocked else "ready for separate PR"
    else:
        state = "current minor"
    rows.append(f"| CPython | {current_python} | {latest_python} | {state} |")
    return rows, actions, candidate if state == "ready for separate PR" else None


def write_minimums(root: Path) -> None:
    path = root / "pyproject.toml"
    text = path.read_text("utf-8")
    parsed = requirements(read_toml(path))
    for req in parsed:
        if req.url or req.marker or len(list(req.specifier)) != 1:
            raise ValueError(f"{req.name}: complex requirements need manual review")
    direct = {canonicalize_name(req.name) for req in parsed}
    inventory = packages(root)

    def replace(match: re.Match) -> str:
        try:
            req = Requirement(match["req"])
        except ValueError:
            return match[0]
        name = canonicalize_name(req.name)
        if name not in direct:
            return match[0]
        if req.url or req.marker or len(list(req.specifier)) != 1:
            raise ValueError(f"{name}: complex requirements need manual review")
        spec = next(iter(req.specifier))
        if spec.operator not in (">=", "=="):
            raise ValueError(f"{name}: unsupported constraint")
        extras = "[" + ",".join(sorted(req.extras)) + "]" if req.extras else ""
        operator = "==" if name.startswith("agent-framework") else spec.operator
        return f"{match['quote']}{req.name}{extras}{operator}{inventory[name][0]}{match['quote']}"

    path.write_text(DEPENDENCY.sub(replace, text), encoding="utf-8", newline="\n")


def write_actions(root: Path, actions: dict[str, tuple[str, str]]) -> None:
    for path in workflows(root):

        def replace(match: re.Match) -> str:
            tag, sha = actions[match["repo"]]
            return f"{match['prefix']}{match['repo']}@{sha} # {tag}"

        path.write_text(
            ACTION.sub(replace, path.read_text("utf-8")), encoding="utf-8", newline="\n"
        )


def write_backend(root: Path) -> None:
    path = root / "pyproject.toml"
    project = read_toml(path)
    text = path.read_text("utf-8")
    for raw in project.get("build-system", {}).get("requires", []):
        req = Requirement(raw)
        if canonicalize_name(req.name) != "uv-build":
            raise ValueError("Extend backend refresh support before changing the build system")
        latest = latest_package(fetch("https://pypi.org/pypi/uv_build/json"), False)
        parsed = Version(latest)
        replacement = f"uv_build>={latest},<{parsed.major}.{parsed.minor + 1}"
        text = text.replace(f'"{raw}"', f'"{replacement}"')
    path.write_text(text, encoding="utf-8", newline="\n")


def write_python(root: Path, minor: str) -> None:
    if not re.fullmatch(r"3\.\d+", minor):
        raise ValueError("Expected a CPython minor such as 3.15")
    old = (root / ".python-version").read_text("utf-8").strip()
    if Version(minor) <= Version(old):
        raise ValueError("Interpreter updates must increase the minor version")
    path = root / "pyproject.toml"
    text = path.read_text("utf-8").replace(
        f'requires-python = ">={old}"', f'requires-python = ">={minor}"'
    )
    text = text.replace(
        f'target-version = "py{old.replace(".", "")}"',
        f'target-version = "py{minor.replace(".", "")}"',
    )
    text = text.replace(f'python_version = "{old}"', f'python_version = "{minor}"')
    path.write_text(text, encoding="utf-8", newline="\n")
    (root / ".python-version").write_text(minor + "\n", encoding="utf-8")
    path = root / "README.md"
    path.write_text(
        path.read_text("utf-8").replace(f"badge/Python-{old}-", f"badge/Python-{minor}-"),
        encoding="utf-8",
    )


def check_python_wheels(root: Path, minor: str) -> list[str]:
    if not re.fullmatch(r"3\.\d+", minor):
        raise ValueError("Expected a CPython minor")
    blocked = []
    for name, resolutions in packages(root).items():
        for version in resolutions:
            files = fetch(f"https://pypi.org/pypi/{name}/{version}/json")["urls"]
            if not wheel_ready(files, minor):
                blocked.append(f"{name}=={version} has no compatible wheels for Python {minor}")
    return blocked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-upstream", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--write-minimums", action="store_true")
    mode.add_argument("--write-python")
    mode.add_argument("--check-python-wheels")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--candidate-file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.check_python_wheels:
            errors = check_python_wheels(ROOT, args.check_python_wheels)
            print("\n".join(errors) if errors else "Python wheel compatibility checks passed.")
            return int(bool(errors))
        if args.check:
            errors = check(ROOT)
            print("\n".join(errors) if errors else "Version consistency checks passed.")
            return int(bool(errors))
        if args.write_python:
            write_python(ROOT, args.write_python)
            return 0
        if args.write_minimums:
            write_minimums(ROOT)
            return 0
        rows, actions, candidate = upstream(ROOT)
        report = "\n".join(rows) + "\n"
        print(report)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(report, encoding="utf-8")
        if args.candidate_file:
            args.candidate_file.parent.mkdir(parents=True, exist_ok=True)
            args.candidate_file.write_text(candidate or "", encoding="utf-8")
        if args.write:
            write_backend(ROOT)
            write_actions(ROOT, actions)
            write_minimums(ROOT)
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"Version inventory failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
