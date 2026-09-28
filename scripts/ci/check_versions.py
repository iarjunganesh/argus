"""Inventory the Python, action, image and web surfaces; check offline or refresh upstream.

Network failures are errors, never evidence that a dependency is current. An unknown base image
fails closed. The web UI's npm packages are pinned exactly; the refresh moves each one to the
newest release of its major version and reports a new major for review, because npm peer ranges
(ESLint plugins, typescript-eslint) often lag a major release.
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
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
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
FROM_LINE = re.compile(
    r"^FROM\s+(?:--platform=\S+\s+)?(?P<ref>\S+)(?:\s+AS\s+(?P<stage>\S+))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
IMAGE_PIN = re.compile(
    r"(?P<image>[a-z0-9][\w./-]*):(?P<tag>(?P<version>\d+(?:\.\d+)*)(?P<suffix>[\w.-]*))"
    r"@(?P<digest>sha256:[0-9a-f]{64})"
)
# Every base image the Dockerfile may use: where its registry keeps it, and where its releases
# are read (`cpython` = CPython's tags; otherwise a GitHub repository's latest release).
IMAGES = {
    "python": {"registry": "docker.io", "repository": "library/python", "releases": "cpython"},
    "ghcr.io/astral-sh/uv": {
        "registry": "ghcr.io",
        "repository": "astral-sh/uv",
        "releases": "astral-sh/uv",
    },
}


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
    problems = [
        *_python_target_problems(project, locked, pinned),
        *_requirement_problems(root, project, locked),
        *_workflow_problems(root, pinned),
        *_image_problems(root, pinned),
    ]
    problems += _web_problems(root)
    return problems


# ── web (npm) ────────────────────────────────────────────────────────────────

WEB = "web"
NPM_SECTIONS = ("dependencies", "devDependencies")
SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def web_manifest(root: Path) -> dict | None:
    path = root / WEB / "package.json"
    return json.loads(path.read_text("utf-8")) if path.exists() else None


def web_pins(manifest: dict) -> dict[str, str]:
    return {
        name: spec for section in NPM_SECTIONS for name, spec in manifest.get(section, {}).items()
    }


def node_major(root: Path) -> str:
    path = root / WEB / ".nvmrc"
    return path.read_text("utf-8").strip() if path.exists() else ""


def semver(version: str) -> tuple[int, int, int] | None:
    """A stable `major.minor.patch` version; None for ranges, tags and prereleases."""
    match = SEMVER.fullmatch(version)
    return (int(match[1]), int(match[2]), int(match[3])) if match else None


def _web_problems(root: Path) -> list[str]:
    manifest = web_manifest(root)
    if manifest is None:
        return []
    lock_path = root / WEB / "package-lock.json"
    if not lock_path.exists():
        return ["web: package-lock.json is missing"]
    installed = json.loads(lock_path.read_text("utf-8")).get("packages", {})
    problems = [
        f"web: package-lock.json {section} disagree with package.json"
        for section in NPM_SECTIONS
        if installed.get("", {}).get(section, {}) != manifest.get(section, {})
    ]
    for name, spec in web_pins(manifest).items():
        if semver(spec) is None:
            problems.append(f"web: {name} needs an exact version, not {spec}")
        elif installed.get(f"node_modules/{name}", {}).get("version") != spec:
            problems.append(f"web: {name} {spec} disagrees with package-lock.json")
    return problems + _node_problems(root, manifest)


def _node_problems(root: Path, manifest: dict) -> list[str]:
    node = node_major(root)
    if not node.isdigit():
        return ["web: .nvmrc must name a Node.js major version"]
    problems = []
    if manifest.get("engines", {}).get("node") != f">={node}":
        problems.append(f"web: engines.node disagrees with .nvmrc ({node})")
    types = semver(web_pins(manifest).get("@types/node", ""))
    if types and str(types[0]) != node:
        problems.append(f"web: @types/node disagrees with Node.js {node}")
    for path in workflows(root):
        problems.extend(
            f"{path.name}: Node.js {value} disagrees with {node}"
            for value in re.findall(r"node-version:\s*['\"]?(\d+)", path.read_text("utf-8"))
            if value != node
        )
    return problems


def image_refs(root: Path) -> list[str]:
    """The Dockerfile's base images, in order, without references to its own stages."""
    path = root / "Dockerfile"
    if not path.exists():
        return []
    refs, stages = [], set()
    for match in FROM_LINE.finditer(path.read_text("utf-8")):
        if match["ref"].lower() not in stages:
            refs.append(match["ref"])
        if match["stage"]:
            stages.add(match["stage"].lower())
    return refs


def _image_problems(root: Path, pinned: str) -> list[str]:
    problems = []
    seen: dict[str, str] = {}
    for ref in image_refs(root):
        pin = IMAGE_PIN.fullmatch(ref)
        if not pin:
            problems.append(f"Dockerfile: {ref} needs a version tag and a sha256 digest")
            continue
        image = pin["image"]
        if image not in IMAGES:
            problems.append(f"Dockerfile: extend the image inventory for {image}")
        if seen.setdefault(image, ref) != ref:
            problems.append(f"Dockerfile: {image}: inconsistent image pins")
        if image == "python" and not pin["version"].startswith(pinned + "."):
            problems.append(f"Dockerfile: python:{pin['tag']} disagrees with {pinned}")
    return problems


def _python_target_problems(project: dict, locked: dict, pinned: str) -> list[str]:
    problems = [
        f"{label}: requires-python disagrees with .python-version"
        for label, value in [
            ("project", project["project"]["requires-python"]),
            ("lock", locked["requires-python"]),
        ]
        if value != f">={pinned}"
    ]
    if project["tool"]["ruff"]["target-version"] != "py" + pinned.replace(".", ""):
        problems.append("Ruff target disagrees with .python-version")
    if project["tool"]["mypy"]["python_version"] != pinned:
        problems.append("Mypy target disagrees with .python-version")
    return problems


def _requirement_problems(root: Path, project: dict, locked: dict) -> list[str]:
    problems = []
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
    return problems


def _workflow_problems(root: Path, pinned: str) -> list[str]:
    problems = []
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
        problems.extend(
            f"{path.name}: Python {value} disagrees with {pinned}"
            for value in re.findall(r"python-version:\s*['\"]?([\d.]+)", text)
            if value != pinned
        )
    return problems


# The only hosts the inventory reads from. Every path segment taken from repository files (package
# names, action repositories, tags) is percent-encoded by `api_url`, so none can change the path.
API_HOSTS = {
    "pypi": "pypi.org",
    "github": "api.github.com",
    "docker-auth": "auth.docker.io",
    "docker-registry": "registry-1.docker.io",
    "ghcr": "ghcr.io",
    "npm": "registry.npmjs.org",
    "node": "nodejs.org",
}
# For each registry: the host that issues anonymous pull tokens, the token path and fixed query,
# and the host that serves manifests.
REGISTRIES = {
    "docker.io": ("docker-auth", ("token",), {"service": "registry.docker.io"}, "docker-registry"),
    "ghcr.io": ("ghcr", ("token",), {}, "ghcr"),
}
MANIFEST_TYPES = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)
USER_AGENT = "ARGUS-dependency-inventory"


def api_url(host: str, *segments: str, query: dict[str, str] | None = None) -> str:
    url = f"https://{API_HOSTS[host]}/" + "/".join(quote(part, safe="") for part in segments)
    if query:
        url += "?" + "&".join(f"{key}={quote(value, safe='')}" for key, value in query.items())
    return url


def _checked(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc not in API_HOSTS.values():
        raise ValueError(f"Refusing a URL outside the inventory's hosts: {url}")
    return url


@cache
def fetch(url: str):
    _checked(url)
    headers = {"User-Agent": USER_AGENT}
    if url.startswith("https://api.github.com/") and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    if url.startswith("https://registry.npmjs.org/"):
        # The abbreviated package document: versions and dist-tags, without the READMEs.
        headers["Accept"] = "application/vnd.npm.install-v1+json"
    request = Request(url, headers=headers)  # noqa: S310 - https only, checked above
    with urlopen(request, timeout=30) as response:  # noqa: S310 - https only, checked above
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
    owner, name = repo.split("/", 1)
    release = fetch(api_url("github", "repos", owner, name, "releases", "latest"))
    tag = release["tag_name"]
    if not re.fullmatch(r"v\d+(?:\.\d+){0,2}", tag):
        raise ValueError(f"{repo}: unsupported release tag")
    obj = fetch(api_url("github", "repos", owner, name, "git", "ref", "tags", tag))["object"]
    for _ in range(5):
        if obj["type"] == "commit":
            if not re.fullmatch(r"[0-9a-f]{40}", obj["sha"]):
                raise ValueError(f"{repo}: invalid commit SHA")
            return tag, obj["sha"]
        if obj["type"] != "tag":
            break
        obj = fetch(api_url("github", "repos", owner, name, "git", "tags", obj["sha"]))["object"]
    raise ValueError(f"{repo}: could not resolve release to a commit")


def registry_digest(image: str, tag: str) -> str | None:
    """The digest the registry serves for `image:tag`, or None if that tag is not published."""
    config = IMAGES[image]
    auth_host, auth_path, auth_query, manifest_host = REGISTRIES[config["registry"]]
    repository = config["repository"]
    scope = {**auth_query, "scope": f"repository:{repository}:pull"}
    token = fetch(api_url(auth_host, *auth_path, query=scope))["token"]
    url = _checked(api_url(manifest_host, "v2", *repository.split("/"), "manifests", tag))
    headers = {
        "Accept": MANIFEST_TYPES,
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
    }
    request = Request(url, method="HEAD", headers=headers)  # noqa: S310 - https only, checked
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - https only, checked above
            digest = response.headers.get("Docker-Content-Digest", "")
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError(f"{image}:{tag}: the registry returned no valid digest")
    return digest


def cpython_releases() -> list[Version]:
    refs = fetch(
        api_url("github", "repos", "python", "cpython", "git", "matching-refs", "tags", "v3.")
    )
    return [
        Version(ref["ref"].rsplit("/", 1)[1][1:])
        for ref in refs
        if re.fullmatch(r"refs/tags/v3\.\d+\.\d+", ref["ref"])
    ]


def latest_image_release(image: str, current: Version) -> Version:
    """The newest release for an image: for Python, the newest patch of the same minor."""
    source = IMAGES[image]["releases"]
    if source == "cpython":
        return max(v for v in cpython_releases() if v.release[:2] == current.release[:2])
    owner, name = source.split("/", 1)
    tag = fetch(api_url("github", "repos", owner, name, "releases", "latest"))["tag_name"]
    return Version(tag.removeprefix("v"))


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


def upstream(
    root: Path,
) -> tuple[list[str], dict[str, tuple[str, str]], dict[str, str], dict[str, str], str | None]:
    """Report rows; action, image (old -> new) and npm pins to write; the Python candidate."""
    inventory = packages(root)
    rows = ["| Surface | Locked | Latest | Status |", "| --- | --- | --- | --- |"]
    metadata = {name: fetch(api_url("pypi", "pypi", name, "json")) for name in sorted(inventory)}
    rows += _package_rows(inventory, metadata)
    rows += _build_rows(root)
    action_rows, actions = _action_rows(root)
    rows += action_rows
    image_rows, images = _image_rows(root)
    rows += image_rows
    npm_rows, npm = _npm_rows(root)
    rows += npm_rows
    python_row, candidate = _python_row(root, inventory, metadata)
    rows.append(python_row)
    return rows, actions, images, npm, candidate


def _package_rows(inventory: dict[str, list[str]], metadata: dict) -> list[str]:
    rows = []
    for name, versions in sorted(inventory.items()):
        allow_pre = name.startswith("agent-framework") and any(
            Version(v).is_prerelease for v in versions
        )
        latest = latest_package(metadata[name], allow_pre)
        current = min(map(Version, versions))
        status = "current"
        if Version(latest) > current:
            status = "MAJOR" if Version(latest).major > current.major else "update"
        rows.append(f"| {name} | {', '.join(versions)} | {latest} | {status} |")
    return rows


def _build_rows(root: Path) -> list[str]:
    rows = []
    for raw in read_toml(root / "pyproject.toml").get("build-system", {}).get("requires", []):
        req = Requirement(raw)
        latest = latest_package(fetch(api_url("pypi", "pypi", req.name, "json")), False)
        status = "within range" if req.specifier.contains(latest) else "update build range"
        rows.append(f"| Build: {req.name} | {req.specifier} | {latest} | {status} |")
    return rows


def _action_rows(root: Path) -> tuple[list[str], dict[str, tuple[str, str]]]:
    rows = []
    actions: dict[str, tuple[str, str]] = {}
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
    return rows, actions


def _image_rows(root: Path) -> tuple[list[str], dict[str, str]]:
    """One row per base image, and the new pin wherever its tag or its digest moved."""
    rows = []
    updates: dict[str, str] = {}
    for ref in dict.fromkeys(image_refs(root)):
        pin = IMAGE_PIN.fullmatch(ref)
        if not pin or pin["image"] not in IMAGES:
            raise ValueError(f"Dockerfile: {ref} is not an inventoried, pinned image")
        image, current = pin["image"], Version(pin["version"])
        latest = latest_image_release(image, current)
        tag = f"{max(latest, current)}{pin['suffix']}"
        digest = registry_digest(image, tag)
        if digest is None:
            status = "not published yet"
        elif digest == pin["digest"]:
            status = "current"
        else:
            status = _image_status(latest, current, tag != pin["tag"])
            updates[ref] = f"{image}:{tag}@{digest}"
        rows.append(f"| Image: {image} | {pin['tag']} | {latest} | {status} |")
    return rows, updates


def _image_status(latest: Version, current: Version, new_tag: bool) -> str:
    if latest.major > current.major:
        return "MAJOR"
    # A rebuilt image keeps its tag and gets a new digest, usually for base-OS security fixes.
    return "update" if new_tag else "rebuilt"


def npm_release(name: str, major: int) -> tuple[str, str]:
    """The newest stable release of `name`, and the newest one within `major`."""
    data = fetch(api_url("npm", name))
    latest = data.get("dist-tags", {}).get("latest", "")
    in_major = [v for v in map(semver, data.get("versions", {})) if v and v[0] == major]
    if semver(latest) is None or not in_major:
        raise ValueError(f"{name}: no stable npm release for major {major}")
    return latest, ".".join(map(str, max(in_major)))


def latest_node_lts(major: int) -> tuple[int, str]:
    """The newest LTS major of Node.js, and the newest release of `major`."""
    releases = [r for r in fetch(api_url("node", "dist", "index.json")) if r.get("lts")]
    versions = [v for v in (semver(r["version"].removeprefix("v")) for r in releases) if v]
    in_major = [v for v in versions if v[0] == major]
    if not in_major:
        raise ValueError(f"Node.js {major} is not an LTS release")
    return max(versions)[0], ".".join(map(str, max(in_major)))


def _npm_rows(root: Path) -> tuple[list[str], dict[str, str]]:
    """One row per npm package and one for Node.js, and the pins that move within their major."""
    manifest = web_manifest(root)
    if manifest is None:
        return [], {}
    node = int(node_major(root))
    rows, updates = [], {}
    for name, spec in sorted(web_pins(manifest).items()):
        current = semver(spec)
        if current is None:
            raise ValueError(f"web: {name} is not pinned exactly")
        # @types/node follows the Node.js major the site runs on, not the newest Node.js.
        major = node if name == "@types/node" else current[0]
        latest, target = npm_release(name, major)
        if name == "@types/node":
            latest = target
        status = "current" if latest == spec else "update"
        if int(latest.split(".")[0]) > current[0]:
            status = "MAJOR"
        if target != spec:
            updates[name] = target
        rows.append(f"| npm: {name} | {spec} | {latest} | {status} |")
    lts, newest = latest_node_lts(node)
    state = f"new LTS {lts}: move web/.nvmrc by hand" if lts > node else "current LTS"
    rows.append(f"| Node.js | {node} | {newest} | {state} |")
    return rows, updates


def write_npm(root: Path, updates: dict[str, str]) -> None:
    """Move npm pins in web/package.json; `npm install` then relocks."""
    if not updates:
        return
    path = root / WEB / "package.json"
    manifest = json.loads(path.read_text("utf-8"))
    for section in NPM_SECTIONS:
        for name in manifest.get(section, {}):
            if name in updates:
                manifest[section][name] = updates[name]
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")


def _python_row(
    root: Path, inventory: dict[str, list[str]], metadata: dict
) -> tuple[str, str | None]:
    """The CPython row, and the next minor version if every locked package is ready for it."""
    latest_python = max(cpython_releases())
    candidate = f"{latest_python.major}.{latest_python.minor}"
    current_python = (root / ".python-version").read_text("utf-8").strip()
    if Version(candidate) > Version(current_python):
        blocked = [
            f"{name}=={version}"
            for name, versions in inventory.items()
            for version in versions
            if not wheel_ready(metadata[name]["releases"][version], candidate)
        ]
        state = "blocked: " + ", ".join(blocked) if blocked else "ready for separate PR"
    else:
        state = "current minor"
    row = f"| CPython | {current_python} | {latest_python} | {state} |"
    return row, candidate if state == "ready for separate PR" else None


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


def write_images(root: Path, updates: dict[str, str]) -> None:
    if not updates:
        return
    path = root / "Dockerfile"
    text = path.read_text("utf-8")
    for old, new in updates.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")


def _python_image_update(root: Path, minor: str) -> dict[str, str]:
    """Move the Dockerfile's Python image to the newest published patch of `minor`."""
    pins = [p for p in map(IMAGE_PIN.fullmatch, image_refs(root)) if p and p["image"] == "python"]
    if not pins:
        return {}
    pin = pins[0]
    latest = max(v for v in cpython_releases() if f"{v.major}.{v.minor}" == minor)
    tag = f"{latest}{pin['suffix']}"
    digest = registry_digest("python", tag)
    if digest is None:
        raise ValueError(f"python:{tag} is not published yet")
    return {pin[0]: f"python:{tag}@{digest}"}


def write_backend(root: Path) -> None:
    path = root / "pyproject.toml"
    project = read_toml(path)
    text = path.read_text("utf-8")
    for raw in project.get("build-system", {}).get("requires", []):
        req = Requirement(raw)
        if canonicalize_name(req.name) != "uv-build":
            raise ValueError("Extend backend refresh support before changing the build system")
        latest = latest_package(fetch(api_url("pypi", "pypi", "uv_build", "json")), False)
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
    write_images(root, _python_image_update(root, minor))
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
            files = fetch(api_url("pypi", "pypi", name, version, "json"))["urls"]
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
        rows, actions, images, npm, candidate = upstream(ROOT)
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
            write_images(ROOT, images)
            write_npm(ROOT, npm)
            write_minimums(ROOT)
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"Version inventory failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
