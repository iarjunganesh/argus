"""The deployment helpers in infra/: which Azure CLI commands they run, and in what order.

The Azure CLI is replaced by a recorder, so nothing here reaches Azure.
"""

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# infra/ is not a package: its scripts import each other by name from their own folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "infra"))

import azcli
import populate
import teardown

RESOURCES = [
    {"name": "argus-ai-x", "type": teardown.COGNITIVE, "location": "swedencentral"},
    {"name": "argus-logs-x", "type": teardown.WORKSPACE, "location": "swedencentral"},
    {"name": "argus-api", "type": "Microsoft.App/containerApps", "location": "swedencentral"},
]


class FakeAz:
    """Records each command; answers from a table keyed by its first words."""

    def __init__(self, answers=None):
        self.calls = []
        self.answers = answers or {}

    def __call__(self, *args):
        self.calls.append(args)
        for prefix, answer in self.answers.items():
            if args[: len(prefix)] == prefix:
                if isinstance(answer, Exception):
                    raise answer
                return answer
        return ""


# ── azcli ─────────────────────────────────────────────────────────────────────


def test_az_needs_the_cli_on_path(monkeypatch):
    monkeypatch.setattr(azcli.shutil, "which", lambda name: None)

    with pytest.raises(azcli.AzError, match="not installed"):
        azcli.az("group", "list")


def test_az_returns_output_and_raises_the_error_text(monkeypatch):
    runs = []

    def run(command, **kwargs):
        runs.append(command)
        if "fail" in command:
            return SimpleNamespace(returncode=1, stdout="", stderr="ERROR: no such group\n")
        return SimpleNamespace(returncode=0, stdout=' {"a": 1}\n', stderr="")

    monkeypatch.setattr(azcli.shutil, "which", lambda name: "/bin/az")
    monkeypatch.setattr(azcli.subprocess, "run", run)

    assert azcli.az_json("thing", "show") == {"a": 1}
    assert runs[0] == ["/bin/az", "thing", "show", "--output", "json", "--only-show-errors"]
    with pytest.raises(azcli.AzError, match="no such group"):
        azcli.az("fail")


def test_deployment_outputs_are_plain_values(monkeypatch):
    fake = FakeAz({("deployment",): '{"searchName": {"type": "String", "value": "s"}}'})
    monkeypatch.setattr(azcli, "az", fake)

    assert azcli.deployment_outputs("rg") == {"searchName": "s"}
    assert fake.calls[0][5:7] == ("--name", azcli.DEPLOYMENT_NAME)

    monkeypatch.setattr(azcli, "az", FakeAz({("deployment",): "null"}))
    with pytest.raises(azcli.AzError, match="No deployment"):
        azcli.deployment_outputs("rg")


@pytest.mark.parametrize("name", ["rg-argus", "a", "RG_1", "my.group(test)", "grüppe", "x" * 90])
def test_resource_group_names_azure_allows_pass(name):
    assert azcli.resource_group_name(name) == name


@pytest.mark.parametrize("name", ["", "-", "--subscription", "rg.", "a b", "rg;ls", "x" * 91])
def test_anything_else_is_refused_before_az_runs(name):
    with pytest.raises(argparse.ArgumentTypeError):
        azcli.resource_group_name(name)


@pytest.mark.parametrize("script", [teardown, populate])
def test_both_scripts_refuse_an_option_as_the_resource_group(script, monkeypatch):
    monkeypatch.setattr(script, "az", FakeAz())

    with pytest.raises(SystemExit) as exit_:
        script.main(["--resource-group=--subscription"])
    assert exit_.value.code == 2


# ── teardown ──────────────────────────────────────────────────────────────────


def test_a_dry_run_lists_and_deletes_nothing(monkeypatch, capsys):
    fake = FakeAz()
    monkeypatch.setattr(teardown, "az_json", lambda *args: RESOURCES)
    monkeypatch.setattr(teardown, "az", fake)

    assert teardown.main(["--resource-group", "rg"]) == 0

    assert fake.calls == []
    out = capsys.readouterr().out
    assert "3 resources in rg" in out and "argus-api" in out and "Dry run" in out


def test_deleting_forgets_the_workspace_then_the_group_then_purges(monkeypatch):
    fake = FakeAz()
    monkeypatch.setattr(teardown, "az_json", lambda *args: RESOURCES)
    monkeypatch.setattr(teardown, "az", fake)

    assert teardown.main(["--resource-group", "rg", "--yes"]) == 0

    assert [c[:3] for c in fake.calls] == [
        ("monitor", "log-analytics", "workspace"),
        ("group", "delete", "--name"),
        ("cognitiveservices", "account", "purge"),
    ]
    assert "--force" in fake.calls[0]
    assert fake.calls[2][-2:] == ("--location", "swedencentral")


def test_teardown_reports_a_cli_error(monkeypatch, capsys):
    def fail(*args):
        raise azcli.AzError("ResourceGroupNotFound")

    monkeypatch.setattr(teardown, "az_json", fail)

    assert teardown.main(["--resource-group", "rg"]) == 1
    assert "ResourceGroupNotFound" in capsys.readouterr().out


# ── populate ──────────────────────────────────────────────────────────────────

OUTPUTS = {"searchName": "s", "cosmosEndpoint": "https://c/", "cosmosDatabase": "argus-db"}


def test_the_steps_reach_the_deployment_named_and_ignore_dotenv(monkeypatch):
    fake = FakeAz({("search", "admin-key"): "admin-key"})
    monkeypatch.setattr(populate, "deployment_outputs", lambda rg: OUTPUTS)
    monkeypatch.setattr(populate, "az", fake)
    monkeypatch.setenv("COSMOS_KEY", "stale")

    env = populate.step_environment("rg")

    assert env["AZURE_SEARCH_ENDPOINT"] == "https://s.search.windows.net"
    assert env["AZURE_SEARCH_API_KEY"] == "admin-key"
    assert env["COSMOS_ENDPOINT"] == "https://c/" and env["COSMOS_DATABASE"] == "argus-db"
    assert env["COSMOS_KEY"] == "" and env["ARGUS_DISABLE_DOTENV"] == "1"
    assert fake.calls[0][-2:] == ("--output", "tsv")


def test_populate_needs_generated_data(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(populate, "ROOT", tmp_path)

    assert populate.main(["--resource-group", "rg"]) == 1
    assert "entities" in capsys.readouterr().out


def test_populate_runs_every_step_and_stops_at_a_failure(monkeypatch, capsys):
    ran = []

    def run(command, env, check):
        ran.append(Path(command[1]).name)
        return SimpleNamespace(returncode=3 if len(ran) == 2 else 0)

    monkeypatch.setattr(populate, "missing_data", list)
    monkeypatch.setattr(populate, "step_environment", lambda rg: {})
    monkeypatch.setattr(populate.subprocess, "run", run)

    assert populate.main(["--resource-group", "rg"]) == 3
    assert ran == ["create_knowledge_bases.py", "index_regulations.py"]

    ran.clear()
    monkeypatch.setattr(
        populate.subprocess,
        "run",
        lambda c, env, check: ran.append(c) or SimpleNamespace(returncode=0),
    )
    assert populate.main(["--resource-group", "rg"]) == 0
    assert len(ran) == len(populate.STEPS)


def test_populate_reports_a_cli_error(monkeypatch, capsys):
    def fail(rg):
        raise azcli.AzError("AuthorizationFailed")

    monkeypatch.setattr(populate, "missing_data", list)
    monkeypatch.setattr(populate, "step_environment", fail)

    assert populate.main(["--resource-group", "rg"]) == 1
    assert "AuthorizationFailed" in capsys.readouterr().out
