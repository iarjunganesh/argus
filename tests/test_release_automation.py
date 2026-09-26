"""Offline regression tests for release gates and dependency automation."""

import importlib.util
import json
import subprocess
from pathlib import Path

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


@pytest.mark.parametrize("path", ["Dockerfile", "web/package.json"])
def test_future_surfaces_cannot_silently_escape_inventory(repo, path):
    target = repo / path
    target.parent.mkdir(exist_ok=True)
    target.touch()
    assert any("Extend the version inventory" in e for e in versions.check(repo))


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
    rows, actions, candidate = versions.upstream(repo)
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
