"""Offline regression tests for release gates and dependency automation."""

import importlib.util
import json
import subprocess
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/ci/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


versions = load("check_versions")
notes = load("release_notes")
refresh = load("refresh_dependencies")


@pytest.fixture
def repo(tmp_path):
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / ".python-version").write_text("3.14\n")
    (tmp_path / "README.md").write_text("badge/Python-3.14-blue")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\nFuture.\n\n## [0.1.0] - 2026-09-26\n\n"
        "### Added\n\n- A tested release.\n\n## [0.0.1]\n\nOld.\n"
    )
    (tmp_path / "pyproject.toml").write_text("""[project]
name = "argus"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["sample[extra]>=1.0"]
[dependency-groups]
dev = ["checker>=2.0"]
[tool.ruff]
target-version = "py314"
[tool.mypy]
python_version = "3.14"
""")
    (tmp_path / "uv.lock").write_text("""requires-python = ">=3.14"
[[package]]
name = "argus"
version = "0.1.0"
source = { editable = "." }
[[package]]
name = "sample"
version = "1.1"
source = { registry = "https://pypi.org/simple" }
[[package]]
name = "checker"
version = "2.0"
source = { registry = "https://pypi.org/simple" }
""")
    (tmp_path / ".github/workflows/ci.yml").write_text(
        "steps:\n  - uses: owner/action@" + "a" * 40 + " # v1.0.0\n"
    )
    return tmp_path


def change(path, old, new):
    path.write_text(path.read_text().replace(old, new))


def test_release_section_does_not_include_other_versions(repo):
    assert notes.extract(repo, "v0.1.0") == "### Added\n\n- A tested release.\n"


@pytest.mark.parametrize("tag", ["0.1.0", "v01.1.0", "v0.1.0;echo bad", "v0.1.0-rc", "v0.1.0-rc.0"])
def test_release_rejects_invalid_tags(repo, tag):
    with pytest.raises(ValueError, match="Expected v"):
        notes.extract(repo, tag)


@pytest.mark.parametrize("suffix,pep", [("alpha.1", "a1"), ("beta.2", "b2"), ("rc.3", "rc3")])
def test_release_prerelease_versions(repo, suffix, pep):
    change(repo / "pyproject.toml", 'version = "0.1.0"', f'version = "0.1.0{pep}"')
    change(repo / "CHANGELOG.md", "[0.1.0]", f"[0.1.0-{suffix}]")
    assert "tested release" in notes.extract(repo, f"v0.1.0-{suffix}")


def test_release_requires_package_version(repo):
    with pytest.raises(ValueError, match="disagrees"):
        notes.extract(repo, "v0.2.0")


@pytest.mark.parametrize(
    "text", ["## [Unreleased]\nAnything", "## [0.1.0]\n\n", "## [0.1.0]\nOne\n## [0.1.0]\nTwo"]
)
def test_release_requires_unique_nonempty_notes(repo, text):
    (repo / "CHANGELOG.md").write_text(text)
    with pytest.raises(ValueError, match="nonempty"):
        notes.extract(repo, "v0.1.0")


def test_offline_consistency(repo):
    assert versions.check(repo) == []


@pytest.mark.parametrize(
    "filename,old,new,expected",
    [
        ("pyproject.toml", ">=3.14", ">=3.13", "requires-python"),
        ("uv.lock", ">=3.14", ">=3.13", "requires-python"),
        ("pyproject.toml", "py314", "py313", "Ruff"),
        ("pyproject.toml", 'python_version = "3.14"', 'python_version = "3.13"', "Mypy"),
        ("uv.lock", 'version = "0.1.0"', 'version = "0.2.0"', "Project version"),
        ("pyproject.toml", "sample[extra]>=1.0", "sample>=9.0", "requirement"),
        ("pyproject.toml", "sample[extra]>=1.0", "missing>=1.0", "requirement"),
        (".github/workflows/ci.yml", "a" * 40, "v1", "full SHA"),
        (".github/workflows/ci.yml", " # v1.0.0", "", "version comment"),
    ],
)
def test_offline_detects_drift(repo, filename, old, new, expected):
    change(repo / filename, old, new)
    assert any(expected in error for error in versions.check(repo))


def test_action_pin_disagreement_and_python_literal(repo):
    (repo / ".github/workflows/release.yml").write_text(
        "uses: owner/action@" + "b" * 40 + " # v2.0.0\npython-version: '3.13'\n"
    )
    errors = versions.check(repo)
    assert any("inconsistent" in e for e in errors)
    assert any("Python 3.13" in e for e in errors)


# ── Web UI (npm) ─────────────────────────────────────────────────────────────


def web(repo, dependencies=None, dev=None, installed=None, node="24"):
    """A web/ folder: package.json, its lock and .nvmrc, consistent unless told otherwise."""
    dependencies = {"next": "16.3.6"} if dependencies is None else dependencies
    dev = {"@types/node": "24.19.0", "eslint": "9.39.5"} if dev is None else dev
    pins = {**dependencies, **dev}
    installed = pins if installed is None else installed
    (repo / "web").mkdir(exist_ok=True)
    manifest = {
        "name": "argus-web",
        "engines": {"node": ">=24"},
        "dependencies": dependencies,
        "devDependencies": dev,
    }
    (repo / "web/package.json").write_text(json.dumps(manifest, indent=2) + "\n")
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "": {"dependencies": dependencies, "devDependencies": dev},
            **{f"node_modules/{name}": {"version": v} for name, v in installed.items()},
        },
    }
    (repo / "web/package-lock.json").write_text(json.dumps(lock))
    (repo / "web/.nvmrc").write_text(node + "\n")
    badges = [f"badge/Node.js-{node}-", "badge/Next.js-16.3-", "badge/TypeScript-6.0-"]
    (repo / "README.md").write_text("badge/Python-3.14-blue\n" + "\n".join(badges) + "\n")
    return repo / "web"


def test_a_consistent_web_surface_passes(repo):
    web(repo)
    (repo / ".github/workflows/web.yml").write_text("node-version-file: web/.nvmrc\n")
    assert versions.check(repo) == []


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"dependencies": {"next": "^16.3.6"}}, "next needs an exact version, not ^16.3.6"),
        ({"installed": {"next": "16.3.5"}}, "next 16.3.6 disagrees with package-lock.json"),
        ({"node": "lts/*"}, ".nvmrc must name a Node.js major version"),
        ({"node": "26"}, "engines.node disagrees with .nvmrc (26)"),
        ({"dev": {"@types/node": "26.6.3"}}, "@types/node disagrees with Node.js 24"),
    ],
)
def test_web_pins_are_checked(repo, kwargs, expected):
    web(repo, **kwargs)
    assert any(expected in error for error in versions.check(repo)), versions.check(repo)


def test_the_lock_must_exist_and_record_the_same_dependencies(repo):
    folder = web(repo)
    lock = json.loads((folder / "package-lock.json").read_text())
    lock["packages"][""]["devDependencies"] = {}
    (folder / "package-lock.json").write_text(json.dumps(lock))
    assert "web: package-lock.json devDependencies disagree with package.json" in (
        versions.check(repo)
    )
    (folder / "package-lock.json").unlink()
    assert "web: package-lock.json is missing" in versions.check(repo)


def test_version_badges_must_show_the_pins(repo):
    web(repo, dev={"typescript": "6.0.3"})
    change(repo / "pyproject.toml", "sample[extra]>=1.0", "agent-framework-core==1.19.0")
    change(
        repo / "uv.lock",
        'name = "sample"\nversion = "1.1"',
        'name = "agent-framework-core"\nversion = "1.19.0"',
    )
    # A package's badge shows its major.minor, followed by any words; Agent Framework, pinned
    # exactly, shows the whole version.
    change(repo / "pyproject.toml", "checker>=2.0", "pytest>=2.0")
    change(repo / "uv.lock", 'name = "checker"', 'name = "pytest"')
    readme = repo / "README.md"
    readme.write_text(
        readme.read_text()
        + "badge/Agent_Framework-1.18.0-0078D4\nbadge/pytest-1.9_passing-0A9EDC\n"
    )
    change(readme, "badge/Next.js-16.3-", "")

    assert versions.check(repo) == [
        "README: the Agent_Framework badge shows 1.18.0, pinned 1.19.0",
        "README: the pytest badge shows 1.9, pinned 2.0",
        "README: no Next.js badge (pinned 16.3)",
    ]

    readme.write_text(readme.read_text() + "badge/Next.js-16.0-000000\n")
    versions.write_badges(repo)
    assert versions.check(repo) == []
    text = readme.read_text()
    assert "badge/Next.js-16.3-000000" in text
    assert "badge/Agent_Framework-1.19.0-0078D4" in text
    assert "badge/pytest-2.0_passing-0A9EDC" in text


def test_workflows_use_the_node_version_of_the_site(repo):
    web(repo)
    (repo / ".github/workflows/web.yml").write_text("with:\n  node-version: '22'\n")
    assert "web.yml: Node.js 22 disagrees with 24" in versions.check(repo)


def npm_document(latest, *versions_):
    return {"dist-tags": {"latest": latest}, "versions": {v: {} for v in versions_}}


NPM = {
    # Current.
    "next": npm_document("16.3.6", "16.3.5", "16.3.6", "16.4.0-canary.1"),
    # A new major: the pin moves to the newest 9.x only.
    "eslint": npm_document("10.1.0", "9.39.5", "9.40.1", "10.1.0"),
    # @types/node follows web/.nvmrc (24), not the newest Node.js.
    "@types/node": npm_document("26.6.3", "24.19.0", "24.20.1", "26.6.3"),
}
NODE = [
    {"version": "v26.10.0", "lts": False},
    {"version": "v24.21.0", "lts": "Krypton"},
    {"version": "v24.20.0", "lts": "Krypton"},
    {"version": "v22.22.0", "lts": "Jod"},
]


def fake_npm(url):
    if url.startswith("https://nodejs.org/"):
        return NODE
    name = unquote(url.removeprefix("https://registry.npmjs.org/"))
    return NPM[name]


def test_upstream_npm_rows_move_pins_within_their_major(repo, monkeypatch):
    web(repo)
    monkeypatch.setattr(versions, "fetch", fake_npm)

    rows, updates = versions._npm_rows(repo)

    assert rows == [
        "| npm: @types/node | 24.19.0 | 24.20.1 | update |",
        "| npm: eslint | 9.39.5 | 10.1.0 | MAJOR |",
        "| npm: next | 16.3.6 | 16.3.6 | current |",
        "| Node.js | 24 | 24.21.0 | current LTS |",
    ]
    assert updates == {"@types/node": "24.20.1", "eslint": "9.40.1"}

    versions.write_npm(repo, updates)
    manifest = json.loads((repo / "web/package.json").read_text())
    assert manifest["devDependencies"] == {"@types/node": "24.20.1", "eslint": "9.40.1"}
    assert manifest["dependencies"] == {"next": "16.3.6"}


def test_a_new_node_lts_is_reported_for_a_manual_move(repo, monkeypatch):
    web(repo, dependencies={}, dev={})
    monkeypatch.setattr(versions, "fetch", lambda url: [*NODE, {"version": "v26.11.0", "lts": "X"}])
    rows, updates = versions._npm_rows(repo)
    assert rows == ["| Node.js | 24 | 24.21.0 | new LTS 26: move web/.nvmrc by hand |"]
    assert updates == {}
    versions.write_npm(repo, updates)  # nothing to write


@pytest.mark.parametrize(
    "document",
    [npm_document("latest-is-not-a-version", "16.3.6"), npm_document("17.0.0", "17.0.0")],
)
def test_npm_release_fails_closed(monkeypatch, document):
    monkeypatch.setattr(versions, "fetch", lambda url: document)
    with pytest.raises(ValueError, match="no stable npm release"):
        versions.npm_release("next", 16)


def test_upstream_needs_exact_npm_pins_and_an_lts_node(repo, monkeypatch):
    monkeypatch.setattr(versions, "fetch", fake_npm)
    assert versions._npm_rows(repo) == ([], {})  # no web UI
    web(repo, dependencies={"next": "latest"}, dev={})
    with pytest.raises(ValueError, match="not pinned exactly"):
        versions._npm_rows(repo)
    web(repo, dependencies={}, dev={}, node="25")
    with pytest.raises(ValueError, match=r"Node.js 25 is not an LTS release"):
        versions._npm_rows(repo)


def test_npm_documents_are_requested_abbreviated(monkeypatch):
    import io

    calls = []

    def fake_open(request, timeout):
        calls.append(request)
        return io.BytesIO(b"{}")

    monkeypatch.setattr(versions, "urlopen", fake_open)
    versions.fetch(versions.api_url("npm", "@types/node"))
    assert calls[0].full_url == "https://registry.npmjs.org/%40types%2Fnode"
    assert calls[0].get_header("Accept") == "application/vnd.npm.install-v1+json"


def test_agent_framework_requires_exact_pin(repo):
    change(repo / "pyproject.toml", "sample[extra]>=1.0", "agent-framework-core>=1.0")
    assert any("exact pin" in error for error in versions.check(repo))


def test_latest_release_ignores_yanked_dev_and_invalid_versions():
    data = {
        "releases": {
            "1.0": [{"yanked": False}],
            "2.0": [{"yanked": True}],
            "3.0rc1": [{}],
            "4.0.dev1": [{}],
            "garbage": [{}],
            "5.0": [],
        }
    }
    assert versions.latest_package(data, False) == "1.0"
    assert versions.latest_package(data, True) == "3.0rc1"
    with pytest.raises(ValueError):
        versions.latest_package({"releases": {}}, False)


@pytest.mark.parametrize("kind", ["commit", "tag"])
def test_action_release_resolves_annotated_tags(monkeypatch, kind):
    answers = iter(
        [
            {"tag_name": "v2.0.0"},
            {"object": {"type": kind, "sha": "b" * 40}},
            {"object": {"type": "commit", "sha": "b" * 40}},
        ]
    )
    monkeypatch.setattr(versions, "fetch", lambda _: next(answers))
    assert versions.action_release("owner/action") == ("v2.0.0", "b" * 40)


@pytest.mark.parametrize(
    "answers",
    [
        [{"tag_name": "bad"}],
        [{"tag_name": "v2"}, {"object": {"type": "commit", "sha": "bad"}}],
        [{"tag_name": "v2"}, {"object": {"type": "tree", "sha": "a" * 40}}],
    ],
)
def test_action_resolution_fails_closed(monkeypatch, answers):
    iterator = iter(answers)
    monkeypatch.setattr(versions, "fetch", lambda _: next(iterator))
    with pytest.raises(ValueError):
        versions.action_release("owner/action")


def wheel(filename="sample-1.0-py3-none-any.whl", **extra):
    return {"filename": filename, "yanked": False, **extra}


def test_wheel_gate_supports_universal_and_abi3():
    assert versions.wheel_ready([wheel()], "3.15")
    assert versions.wheel_ready(
        [
            wheel("sample-1.0-cp39-abi3-win_amd64.whl"),
            wheel("sample-1.0-cp39-abi3-manylinux_2_17_x86_64.whl"),
        ],
        "3.15",
    )


@pytest.mark.parametrize(
    "files",
    [
        [],
        [wheel(yanked=True)],
        [wheel(requires_python="<3.15")],
        [wheel("sample-1.0.tar.gz")],
        [wheel("sample-1.0-cp314-cp314-win_amd64.whl")],
        [wheel("sample-1.0-cp315-cp315-win_amd64.whl")],
    ],
)
def test_wheel_gate_rejects_unready_packages(files):
    assert not versions.wheel_ready(files, "3.15")


def test_interpreter_pr_rechecks_its_own_lock(repo, monkeypatch):
    monkeypatch.setattr(versions, "fetch", lambda _: {"urls": [wheel()]})
    assert versions.check_python_wheels(repo, "3.15") == []
    monkeypatch.setattr(versions, "fetch", lambda _: {"urls": []})
    assert len(versions.check_python_wheels(repo, "3.15")) == 2
    with pytest.raises(ValueError):
        versions.check_python_wheels(repo, "bad")


def test_write_minimums_preserves_extras_and_uses_lowest_resolution(repo):
    versions.write_minimums(repo)
    assert '"sample[extra]>=1.1"' in (repo / "pyproject.toml").read_text()
    versions.write_actions(repo, {"owner/action": ("v2.0.0", "b" * 40)})
    assert "@" + "b" * 40 + " # v2.0.0" in (repo / ".github/workflows/ci.yml").read_text()


def test_build_backend_refresh_retains_bounded_range(repo, monkeypatch):
    with (repo / "pyproject.toml").open("a") as stream:
        stream.write('\n[build-system]\nrequires = ["uv_build>=0.12,<0.13"]\n')
    monkeypatch.setattr(versions, "fetch", lambda _: {"releases": {"0.13.2": [wheel()]}})
    versions.write_backend(repo)
    assert '"uv_build>=0.13.2,<0.14"' in (repo / "pyproject.toml").read_text()


@pytest.mark.parametrize(
    "requirement", ["sample>=1,<2", "sample~=1.0", "sample>=1; python_version>'3'"]
)
def test_complex_requirements_need_review(repo, requirement):
    change(repo / "pyproject.toml", "sample[extra]>=1.0", requirement)
    with pytest.raises(ValueError):
        versions.write_minimums(repo)


def test_write_python_only_changes_interpreter_settings(repo):
    versions.write_python(repo, "3.15")
    assert (repo / ".python-version").read_text() == "3.15\n"
    assert "badge/Python-3.15-" in (repo / "README.md").read_text()
    project = versions.read_toml(repo / "pyproject.toml")
    assert project["tool"]["ruff"]["target-version"] == "py315"
    assert project["project"]["dependencies"] == ["sample[extra]>=1.0"]
    with pytest.raises(ValueError):
        versions.write_python(repo, "3.14")
    with pytest.raises(ValueError):
        versions.write_python(repo, "bad")


@pytest.mark.parametrize("ready", [True, False])
def test_upstream_inventory_major_bumps_and_python_gate(repo, monkeypatch, ready):
    def fake_fetch(url):
        if "pypi" in url:
            return {
                "releases": {"1.1": [wheel()] if ready else [], "2.0": [wheel()], "3.0": [wheel()]}
            }
        return [{"ref": "refs/tags/v3.15.0"}, {"ref": "refs/tags/v3.16.0rc1"}]

    monkeypatch.setattr(versions, "fetch", fake_fetch)
    monkeypatch.setattr(versions, "action_release", lambda _: ("v2.0.0", "b" * 40))
    rows, actions, images, npm, candidate = versions.upstream(repo)
    assert images == {} and npm == {}  # no Dockerfile, no web UI
    assert "MAJOR" in "\n".join(rows)
    assert actions["owner/action"] == ("v2.0.0", "b" * 40)
    assert candidate == ("3.15" if ready else None)


def test_upstream_failure_returns_nonzero_without_writing(repo, monkeypatch):
    monkeypatch.setattr(versions, "ROOT", repo)

    def fail(_):
        raise OSError("upstream unavailable")

    monkeypatch.setattr(versions, "fetch", fail)
    original = (repo / "pyproject.toml").read_text()
    assert versions.main(["--write"]) == 1
    assert (repo / "pyproject.toml").read_text() == original


def test_http_token_is_only_sent_to_github(monkeypatch):
    import io

    calls = []

    def fake_open(request, timeout):
        calls.append(request)
        assert timeout == 30
        return io.BytesIO(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(versions, "urlopen", fake_open)
    monkeypatch.setenv("GH_TOKEN", "test-placeholder")
    assert versions.fetch("https://pypi.org/pypi/sample/json") == {"ok": True}
    versions.fetch("https://api.github.com/repos/owner/action/releases/latest")
    assert not calls[0].has_header("Authorization")
    assert calls[1].has_header("Authorization")


def test_inventory_urls_stay_on_their_hosts_and_paths(monkeypatch):
    monkeypatch.setattr(versions, "urlopen", lambda request, timeout: pytest.fail("fetched"))
    for url in ("http://pypi.org/pypi/x/json", "https://example.com/pypi/x/json"):
        with pytest.raises(ValueError, match="outside the inventory's hosts"):
            versions.fetch(url)
    # A name read from a repository file cannot climb out of its path segment.
    assert versions.api_url("pypi", "pypi", "../../admin", "json") == (
        "https://pypi.org/pypi/..%2F..%2Fadmin/json"
    )


def test_refresh_failure_is_reported_and_later_checks_run(repo, monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        assert "UV_LOCKED" not in kwargs["env"]
        return subprocess.CompletedProcess(command, 1 if command == ["broken"] else 0)

    monkeypatch.setattr(refresh.subprocess, "run", fake_run)
    monkeypatch.setenv("UV_LOCKED", "1")
    assert refresh.run(repo, "v0.1.0", [("Upgrade", ["broken"]), ("Test", ["test"])]) == 1
    assert calls == [["broken"], ["test"]]
    report = (repo / "docs/DEPENDENCY-REFRESH.md").read_text()
    assert "| Upgrade | FAIL |" in report
    assert "| Test | PASS |" in report
    assert "Inventory unavailable" in report


@pytest.mark.parametrize("error", [OSError("missing tool"), subprocess.TimeoutExpired("tool", 1)])
def test_refresh_reports_tool_failure(repo, monkeypatch, error):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(refresh.subprocess, "run", fail)
    assert refresh.run(repo, "v0.1.0", [("Tool", ["tool"])]) == 1


def test_refresh_rejects_untrusted_tag(repo):
    with pytest.raises(ValueError):
        refresh.run(repo, "bad/tag", [])


def test_refresh_commands_include_quality_gates():
    labels = {label for label, _ in refresh.commands("python")}
    assert {"Lint", "Format", "Types", "Tests", "Docs", "Versions", "Assets", "Audit"} <= labels
    assert {"Web install", "Web lint", "Web types", "Web tests", "Web build", "Web audit"} <= labels


# ── Container base images ────────────────────────────────────────────────────

UV_DIGEST = "sha256:" + "1" * 64
PY_DIGEST = "sha256:" + "2" * 64
UV_PIN = f"ghcr.io/astral-sh/uv:0.12.19@{UV_DIGEST}"
PY_PIN = f"python:3.14.7-slim-trixie@{PY_DIGEST}"


def dockerfile(repo, text=None):
    text = text or (
        f"FROM {UV_PIN} AS uv\n"
        f"FROM {PY_PIN} AS build\n"
        "COPY --from=uv /uv /usr/local/bin/uv\n"
        f"from --platform=linux/amd64 {PY_PIN} as runtime\n"
        "FROM build AS test\n"
    )
    (repo / "Dockerfile").write_text(text)
    return repo / "Dockerfile"


def test_pinned_base_images_pass_and_stage_references_are_not_images(repo):
    dockerfile(repo)

    assert versions.check(repo) == []
    assert versions.image_refs(repo) == [UV_PIN, PY_PIN, PY_PIN]


@pytest.mark.parametrize(
    "line,expected",
    [
        ("FROM python:3.14.7-slim-trixie", "needs a version tag and a sha256 digest"),
        ("FROM python:latest@" + PY_DIGEST, "needs a version tag"),
        ("FROM debian:13@" + PY_DIGEST, "extend the image inventory for debian"),
        ("FROM python:3.14.8-slim-trixie@" + PY_DIGEST, "inconsistent image pins"),
        ("FROM python:3.13.9-slim@" + PY_DIGEST, "disagrees with 3.14"),
    ],
)
def test_image_pins_are_checked(repo, line, expected):
    dockerfile(repo, f"FROM {PY_PIN}\n{line}\n")

    assert any(expected in error for error in versions.check(repo))


def fake_releases(url):
    if "cpython" in url:
        return [{"ref": f"refs/tags/v{v}"} for v in ("3.14.7", "3.14.8", "3.15.0", "3.15.1rc1")]
    return {"tag_name": "0.13.0"}


@pytest.mark.parametrize(
    "digests,expected_rows,expected_updates",
    [
        (
            {"0.13.0": "sha256:" + "3" * 64, "3.14.8-slim-trixie": "sha256:" + "4" * 64},
            ["| 0.12.19 | 0.13.0 | update |", "| 3.14.7-slim-trixie | 3.14.8 | update |"],
            {
                UV_PIN: "ghcr.io/astral-sh/uv:0.13.0@sha256:" + "3" * 64,
                PY_PIN: "python:3.14.8-slim-trixie@sha256:" + "4" * 64,
            },
        ),
        ({}, ["not published yet"] * 2, {}),
    ],
)
def test_upstream_reports_and_resolves_image_updates(
    repo, monkeypatch, digests, expected_rows, expected_updates
):
    dockerfile(repo)
    monkeypatch.setattr(versions, "fetch", fake_releases)
    monkeypatch.setattr(versions, "registry_digest", lambda image, tag: digests.get(tag))

    rows, updates = versions._image_rows(repo)

    assert len(rows) == 2  # one row per image, however many stages use it
    assert all(expected in row for expected, row in zip(expected_rows, rows, strict=True))
    assert updates == expected_updates


def test_same_tag_with_a_new_digest_is_a_rebuild_and_a_matching_one_is_current(repo, monkeypatch):
    dockerfile(repo, f"FROM {UV_PIN}\nFROM python:3.14.8-slim-trixie@{PY_DIGEST}\n")
    monkeypatch.setattr(versions, "fetch", lambda url: {"tag_name": "v0.12.19"})
    monkeypatch.setattr(versions, "cpython_releases", lambda: [versions.Version("3.14.8")])
    new = "sha256:" + "5" * 64
    monkeypatch.setattr(
        versions, "registry_digest", lambda image, tag: new if image == "python" else UV_DIGEST
    )

    rows, updates = versions._image_rows(repo)

    assert rows[0].endswith("| current |") and rows[1].endswith("| rebuilt |")
    assert updates == {f"python:3.14.8-slim-trixie@{PY_DIGEST}": f"python:3.14.8-slim-trixie@{new}"}


def test_a_major_image_release_is_flagged():
    assert (
        versions._image_status(versions.Version("1.0"), versions.Version("0.12"), True) == "MAJOR"
    )


def test_an_unpinned_image_stops_the_upstream_inventory(repo):
    dockerfile(repo, "FROM python:3.14\n")

    with pytest.raises(ValueError, match="not an inventoried, pinned image"):
        versions._image_rows(repo)


def test_write_images_replaces_every_stage_that_uses_a_pin(repo):
    path = dockerfile(repo)
    versions.write_images(repo, {})  # nothing to do, nothing written
    versions.write_images(repo, {PY_PIN: "python:3.14.8-slim-trixie@" + PY_DIGEST})

    assert path.read_text().count("3.14.8-slim-trixie") == 2
    assert UV_PIN in path.read_text()


def test_write_python_moves_the_python_image_to_the_new_minor(repo, monkeypatch):
    path = dockerfile(repo)
    monkeypatch.setattr(versions, "fetch", fake_releases)
    new = "sha256:" + "6" * 64
    monkeypatch.setattr(versions, "registry_digest", lambda image, tag: new)

    versions.write_python(repo, "3.15")

    assert f"python:3.15.0-slim-trixie@{new}" in path.read_text()
    assert not [e for e in versions.check(repo) if "Dockerfile" in e]  # `uv lock` does the rest


def test_write_python_stops_if_the_new_python_image_is_not_published(repo, monkeypatch):
    dockerfile(repo)
    monkeypatch.setattr(versions, "fetch", fake_releases)
    monkeypatch.setattr(versions, "registry_digest", lambda image, tag: None)

    with pytest.raises(ValueError, match="not published yet"):
        versions.write_python(repo, "3.15")


def test_write_python_without_a_python_image_leaves_the_dockerfile_alone(repo):
    path = dockerfile(repo, f"FROM {UV_PIN}\n")

    versions.write_python(repo, "3.15")

    assert path.read_text() == f"FROM {UV_PIN}\n"


class Response:
    def __init__(self, digest):
        self.headers = {"Docker-Content-Digest": digest}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_registry_digest_asks_for_an_anonymous_token_then_the_manifest(monkeypatch):
    tokens, requests = [], []
    monkeypatch.setattr(versions, "fetch", lambda url: tokens.append(url) or {"token": "t"})

    def fake_open(request, timeout):
        requests.append(request)
        return Response(PY_DIGEST)

    monkeypatch.setattr(versions, "urlopen", fake_open)

    assert versions.registry_digest("python", "3.14.7-slim-trixie") == PY_DIGEST
    assert versions.registry_digest("ghcr.io/astral-sh/uv", "0.12.19") == PY_DIGEST
    assert tokens == [
        "https://auth.docker.io/token?service=registry.docker.io"
        "&scope=repository%3Alibrary%2Fpython%3Apull",
        "https://ghcr.io/token?scope=repository%3Aastral-sh%2Fuv%3Apull",
    ]
    docker, ghcr = requests
    assert docker.full_url == (
        "https://registry-1.docker.io/v2/library/python/manifests/3.14.7-slim-trixie"
    )
    assert docker.get_method() == "HEAD"
    assert docker.get_header("Authorization") == "Bearer t"
    assert "image.index" in docker.get_header("Accept")
    assert ghcr.full_url == "https://ghcr.io/v2/astral-sh/uv/manifests/0.12.19"


def test_registry_digest_of_an_unpublished_tag_is_none_and_other_errors_raise(monkeypatch):
    from urllib.error import HTTPError

    monkeypatch.setattr(versions, "fetch", lambda url: {"token": "t"})
    codes = iter([404, 500])

    def fail(request, timeout):
        raise HTTPError(request.full_url, next(codes), "error", {}, None)

    monkeypatch.setattr(versions, "urlopen", fail)

    assert versions.registry_digest("python", "3.99.0") is None
    with pytest.raises(HTTPError):
        versions.registry_digest("python", "3.99.0")


def test_registry_digest_rejects_a_missing_digest(monkeypatch):
    monkeypatch.setattr(versions, "fetch", lambda url: {"token": "t"})
    monkeypatch.setattr(versions, "urlopen", lambda request, timeout: Response(""))

    with pytest.raises(ValueError, match="no valid digest"):
        versions.registry_digest("python", "3.14.7")


def test_api_url_encodes_query_values():
    assert versions.api_url("ghcr", "token", query={"scope": "a b/c"}) == (
        "https://ghcr.io/token?scope=a%20b%2Fc"
    )


def test_release_notes_go_to_their_fixed_file(repo, monkeypatch, capsys):
    monkeypatch.setattr(notes, "ROOT", repo)
    monkeypatch.setattr(notes, "NOTES", repo / ".tmp" / "release-notes.md")
    monkeypatch.setattr("sys.argv", ["release_notes.py", "v0.1.0"])

    notes.main()

    assert (repo / ".tmp" / "release-notes.md").read_text() == "### Added\n\n- A tested release.\n"
    assert "written to .tmp" in capsys.readouterr().out


def test_the_inventory_writes_its_report_and_candidate_to_fixed_files(tmp_path, monkeypatch):
    monkeypatch.setattr(versions, "upstream", lambda root: (["| row |"], {}, {}, {}, "3.15"))
    monkeypatch.setattr(versions, "REPORTS", {"after": tmp_path / "after.md"})
    monkeypatch.setattr(versions, "CANDIDATE", tmp_path / "candidate.txt")

    assert versions.main(["--check-upstream", "--report", "after", "--write-candidate"]) == 0

    assert (tmp_path / "after.md").read_text() == "| row |\n"
    assert (tmp_path / "candidate.txt").read_text() == "3.15"
