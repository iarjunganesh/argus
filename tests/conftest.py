"""Keep the test suite hermetic.

Set before any ARGUS module is imported: a developer's local .env or shell credentials must not
change which code paths run, so local results match CI, which has neither. The local data plane
reads the small fixture data set in `tests/fixtures/data`, never data generated on this machine.
"""

import os
from pathlib import Path

import pytest

os.environ["ARGUS_DISABLE_DOTENV"] = "1"

_SETTING_PREFIXES = ("AZURE_", "COSMOS_", "FOUNDRY_", "DOC_INTELLIGENCE_", "ARGUS_", "OPENAI_")
_KEEP = {"ARGUS_DISABLE_DOTENV"}
for _name in list(os.environ):
    stale = _name.startswith(_SETTING_PREFIXES) or _name in ("GITHUB_TOKEN", "USE_GITHUB_MODELS")
    if stale and _name not in _KEEP:
        del os.environ[_name]

FIXTURE_DATA = Path(__file__).parent / "fixtures" / "data"
os.environ["ARGUS_DATA_DIR"] = str(FIXTURE_DATA)


@pytest.fixture(autouse=True)
def _fresh_data_plane():
    """Every test starts from the plane its settings describe."""
    from argus.data_plane import set_data_plane

    set_data_plane(None)
    yield
    set_data_plane(None)


@pytest.fixture
def use_plane():
    """Install a data plane that is local except for the parts a test replaces."""
    import dataclasses

    from argus.data_plane import build_data_plane, set_data_plane

    def install(**parts):
        plane = dataclasses.replace(build_data_plane(), **parts)
        set_data_plane(plane)
        return plane

    return install


class Unavailable:
    """Stands in for any data-plane part whose service is down: every call raises."""

    def __getattr__(self, name):
        from argus.data_plane import DataPlaneUnavailable

        async def fail(*args, **kwargs):
            raise DataPlaneUnavailable(f"{name}: service down")

        return fail


@pytest.fixture
def unavailable():
    return Unavailable()


@pytest.fixture
def a2a_request() -> dict:
    """The JSON envelope the orchestrator posts to every agent's /a2a/invoke."""
    return {
        "a2a_version": "1.0",
        "source_agent": "argus-orchestrator-v1",
        "target_agent": "argus-agent-v1",
        "task_id": "test-task-001",
        "payload": {
            "entity_name": "Synthetic Entity Ltd.",
            "entity_type": "corporate",
            "jurisdiction": "NL",
            "aliases": ["SE Ltd"],
        },
    }
