from argus.utils import env_loader


def test_loads_key_values_from_nearest_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("ARGUS_DISABLE_DOTENV")
    monkeypatch.delenv("ARGUS_TEST_KEY", raising=False)
    (tmp_path / ".env").write_text("# comment\n\nARGUS_TEST_KEY = value\nno-equals-line\n")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)

    env_loader.load_repo_env(nested)

    assert env_loader.os.environ["ARGUS_TEST_KEY"] == "value"


def test_existing_variables_win(tmp_path, monkeypatch):
    monkeypatch.delenv("ARGUS_DISABLE_DOTENV")
    monkeypatch.setenv("ARGUS_TEST_KEY", "from-shell")
    (tmp_path / ".env").write_text("ARGUS_TEST_KEY=from-file\n")

    env_loader.load_repo_env(tmp_path / ".env")

    assert env_loader.os.environ["ARGUS_TEST_KEY"] == "from-shell"


def test_disabled_during_tests(tmp_path, monkeypatch):
    monkeypatch.delenv("ARGUS_TEST_KEY", raising=False)
    (tmp_path / ".env").write_text("ARGUS_TEST_KEY=value\n")

    env_loader.load_repo_env(tmp_path)

    assert "ARGUS_TEST_KEY" not in env_loader.os.environ


def test_no_env_file_anywhere_changes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("ARGUS_DISABLE_DOTENV")
    monkeypatch.setattr(env_loader.Path, "exists", lambda self: False)
    before = dict(env_loader.os.environ)

    env_loader.load_repo_env(tmp_path)

    assert dict(env_loader.os.environ) == before
