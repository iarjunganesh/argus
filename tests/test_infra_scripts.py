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

OUTPUTS = {
    "searchName": "s",
    "cosmosEndpoint": "https://c/",
    "cosmosAccount": "argus-cosmos-x",
    "cosmosDatabase": "argus-db",
}
OPERATOR = ("ad", "signed-in-user", "show")
ROLE_LIST = ("cosmosdb", "sql", "role", "assignment", "list")


def test_the_steps_reach_the_deployment_named_and_ignore_dotenv(monkeypatch):
    fake = FakeAz({("search", "admin-key"): "admin-key", OPERATOR: "me", ROLE_LIST: "1"})
    monkeypatch.setattr(populate, "deployment_outputs", lambda rg: OUTPUTS)
    monkeypatch.setattr(populate, "az", fake)
    monkeypatch.setenv("COSMOS_KEY", "stale")

    env = populate.step_environment("rg")

    assert env["AZURE_SEARCH_ENDPOINT"] == "https://s.search.windows.net"
    assert env["AZURE_SEARCH_API_KEY"] == "admin-key"
    assert env["COSMOS_ENDPOINT"] == "https://c/" and env["COSMOS_DATABASE"] == "argus-db"
    assert env["COSMOS_KEY"] == "" and env["ARGUS_DISABLE_DOTENV"] == "1"
    assert fake.calls[-1][:2] == ("search", "admin-key")
    assert fake.calls[-1][-2:] == ("--output", "tsv")


def test_the_operator_gets_the_cosmos_data_role_on_the_database_once(monkeypatch):
    fake = FakeAz({OPERATOR: "me", ROLE_LIST: "0"})
    monkeypatch.setattr(populate, "az", fake)

    assert populate.grant_operator_cosmos_access("rg", OUTPUTS) is True
    create = fake.calls[-1]
    assert create[:5] == ("cosmosdb", "sql", "role", "assignment", "create")
    assert create[create.index("--principal-id") + 1] == "me"
    assert create[create.index("--scope") + 1] == "/dbs/argus-db"
    assert create[create.index("--account-name") + 1] == "argus-cosmos-x"
    assert "principalId=='me'" in fake.calls[1][fake.calls[1].index("--query") + 1]

    fake = FakeAz({OPERATOR: "me", ROLE_LIST: "1"})
    monkeypatch.setattr(populate, "az", fake)
    assert populate.grant_operator_cosmos_access("rg", OUTPUTS) is False
    assert len(fake.calls) == 2 and fake.calls[1][:5] == ROLE_LIST


def test_a_new_role_is_announced(monkeypatch, capsys):
    monkeypatch.setattr(populate, "deployment_outputs", lambda rg: OUTPUTS)
    monkeypatch.setattr(populate, "az", FakeAz({OPERATOR: "me", ROLE_LIST: ""}))

    populate.step_environment("rg")

    assert "Cosmos DB data role" in capsys.readouterr().out


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


# ── filling the data plane: search indexes and Cosmos DB ─────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "infra" / "foundry_iq"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data" / "synthetic"))

import replace_documents  # noqa: E402
import upload_to_cosmos  # noqa: E402


class FakeIndex:
    """A search index: documents by ID; `reject` lists IDs the service refuses."""

    def __init__(self, ids, reject=()):
        self.docs = {i: {"id": i} for i in ids}
        self.reject = set(reject)
        self.batches = []

    def upload_documents(self, batch):
        self.batches.append(len(batch))
        results = []
        for doc in batch:
            ok = doc["id"] not in self.reject
            if ok:
                self.docs[doc["id"]] = doc
            results.append(SimpleNamespace(key=doc["id"], succeeded=ok))
        return results

    def search(self, text, select):
        assert text == "*" and select == ["id"]
        return [{"id": i} for i in list(self.docs)]

    def delete_documents(self, batch):
        for doc in batch:
            del self.docs[doc["id"]]


def test_an_index_ends_up_holding_exactly_the_new_documents():
    index = FakeIndex(["old-1", "kept", "old-2"])
    docs = [{"id": "kept"}, *({"id": f"new-{n}"} for n in range(5))]

    assert replace_documents.replace_documents(index, docs, batch_size=2) == 2

    assert set(index.docs) == {d["id"] for d in docs}
    assert index.batches == [2, 2, 2]


def test_a_rejected_document_stops_before_anything_is_deleted():
    index = FakeIndex(["old"], reject={"bad"})

    with pytest.raises(replace_documents.IndexingFailed, match="1 of 2 documents rejected"):
        replace_documents.replace_documents(index, [{"id": "good"}, {"id": "bad"}])
    assert "old" in index.docs


class FakeContainer:
    """A Cosmos container: items by ID with their partition key value."""

    def __init__(self, items=(), reject=()):
        self.items = {i["id"]: i for i in items}
        self.reject = set(reject)
        self.deleted = []

    def upsert_item(self, doc):
        if doc["id"] in self.reject:
            raise RuntimeError("partition key missing")
        self.items[doc["id"]] = doc

    def query_items(self, query, enable_cross_partition_query):
        assert query == "SELECT c.id, c.entity_type AS pk FROM c" and enable_cross_partition_query
        return [{"id": i["id"], "pk": i["entity_type"]} for i in self.items.values()]

    def delete_item(self, item, partition_key):
        self.deleted.append((item, partition_key))
        del self.items[item]


def test_a_container_ends_up_holding_exactly_the_new_records():
    container = FakeContainer([{"id": "gone", "entity_type": "corporate"}])
    docs = [{"id": "e1", "entity_type": "individual"}]

    assert upload_to_cosmos.replace_items(container, docs, "entity_type") == 1

    assert list(container.items) == ["e1"]
    assert container.deleted == [("gone", "corporate")]


def test_a_rejected_record_stops_before_anything_is_deleted():
    container = FakeContainer([{"id": "old", "entity_type": "corporate"}], reject={"e2"})
    docs = [{"id": "e1", "entity_type": "x"}, {"id": "e2", "entity_type": "x"}]

    with pytest.raises(upload_to_cosmos.UploadFailed, match="1 of 2 records rejected"):
        upload_to_cosmos.replace_items(container, docs, "entity_type")
    assert "old" in container.items and container.deleted == []


def test_records_keep_their_ids_from_run_to_run():
    edge = {"parent_entity": "A", "child_entity": "B"}
    moved = {**edge, "child_entity": "C"}

    first = upload_to_cosmos.with_ids([edge], None)
    assert first == upload_to_cosmos.with_ids([dict(edge)], None)
    assert first[0]["id"] != upload_to_cosmos.with_ids([moved], None)[0]["id"]
    assert upload_to_cosmos.with_ids([{"tx_id": 7}], "tx_id") == [{"tx_id": 7, "id": "7"}]


def test_the_upload_fails_without_generated_data(monkeypatch, tmp_path, capsys):
    import argus.config

    monkeypatch.setattr(upload_to_cosmos, "DATA_DIR", tmp_path)
    monkeypatch.setattr(argus.config, "get_cosmos_database", lambda: SimpleNamespace())

    assert upload_to_cosmos.main() == 1
    assert "entities.jsonl is missing" in capsys.readouterr().out


def test_the_upload_fills_every_container(monkeypatch, capsys):
    import argus.config

    synthetic = Path(__file__).parent / "fixtures" / "data" / "synthetic"
    containers = {}

    class Container(FakeContainer):
        def query_items(self, query, enable_cross_partition_query):
            return []

    def container(name):
        return containers.setdefault(name, Container())

    database = SimpleNamespace(get_container_client=container)
    monkeypatch.setattr(upload_to_cosmos, "DATA_DIR", synthetic)
    monkeypatch.setattr(argus.config, "get_cosmos_database", lambda: database)

    assert upload_to_cosmos.main() == 0
    assert set(containers) == {"entities", "corporate_graph", "transactions"}
    assert all(c.items for c in containers.values())
    assert "upload complete" in capsys.readouterr().out
