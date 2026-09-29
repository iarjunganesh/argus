"""The smoke test's target: a local port, or a deployed API on a host it knows."""

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "smoke_api", Path(__file__).resolve().parents[1] / "scripts/ci/smoke_api.py"
)
smoke_api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke_api)


@pytest.mark.parametrize(
    ("arg", "base"),
    [
        ("8000", "http://127.0.0.1:8000"),
        (
            "https://argus-api.blue-sky-1a2b3c.swedencentral.azurecontainerapps.io/",
            "https://argus-api.blue-sky-1a2b3c.swedencentral.azurecontainerapps.io",
        ),
        ("https://api.argus.arjunganesh.dev", "https://api.argus.arjunganesh.dev"),
    ],
)
def test_targets_it_accepts(arg, base):
    assert smoke_api.target(arg) == base


@pytest.mark.parametrize(
    "arg",
    [
        "0",
        "70000",
        "http://argus-api.swedencentral.azurecontainerapps.io",
        "https://example.com",
        "https://azurecontainerapps.io.example.com",
        "https://argus-api.azurecontainerapps.io/api/v1",
    ],
)
def test_targets_it_refuses(arg):
    with pytest.raises(ValueError):
        smoke_api.target(arg)
