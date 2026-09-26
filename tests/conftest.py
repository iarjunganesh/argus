"""Keep the test suite hermetic.

Set before any ARGUS module is imported: a developer's local .env or shell credentials must not
change which code paths run, so local results match CI, which has neither.
"""

import os

import pytest

os.environ["ARGUS_DISABLE_DOTENV"] = "1"

_CREDENTIAL_PREFIXES = ("AZURE_", "COSMOS_", "FOUNDRY_")
for _name in list(os.environ):
    if _name.startswith(_CREDENTIAL_PREFIXES) or _name in ("GITHUB_TOKEN", "USE_GITHUB_MODELS"):
        del os.environ[_name]


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
