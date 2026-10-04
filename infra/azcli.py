"""The Azure CLI calls that infra/populate.py and infra/teardown.py make.

Each call asks for exactly the fields it needs (`--query`), so no command prints a whole
resource, and a key read here goes into a child process's environment, never to the terminal.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from typing import Any

# The name `az deployment group create` is given in docs/DEPLOYMENT.md and deploy.yml; the
# scripts read the deployment's outputs by it.
DEPLOYMENT_NAME = "argus"


# Azure's rule for resource group names: 1 to 90 letters, digits, underscores, hyphens, periods and
# parentheses, not ending in a period. A name can't start with a hyphen here either, so it can never
# be read as one of az's options.
_RESOURCE_GROUP = re.compile(r"(?!-)[\w().-]{0,89}[\w()-]")


def resource_group_name(value: str) -> str:
    """The `--resource-group` argument of populate.py and teardown.py, checked before any az call."""
    if not _RESOURCE_GROUP.fullmatch(value):
        raise argparse.ArgumentTypeError(f"not a resource group name: {value!r}")
    return value


class AzError(RuntimeError):
    """An Azure CLI command failed; the message is its error output."""


def az(*args: str) -> str:
    """Run one Azure CLI command and return its standard output, stripped."""
    exe = shutil.which("az")  # az.cmd on Windows, which subprocess cannot find by itself
    if exe is None:
        raise AzError("The Azure CLI (az) is not installed or not on PATH.")
    result = subprocess.run(  # noqa: S603 - fixed program, arguments from this repository's scripts
        [exe, *args, "--only-show-errors"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise AzError(result.stderr.strip() or f"az {args[0]} failed")
    return result.stdout.strip()


def az_json(*args: str) -> Any:
    return json.loads(az(*args, "--output", "json") or "null")


def deployment_outputs(resource_group: str) -> dict[str, str]:
    """The outputs of infra/main.bicep's last deployment to the resource group."""
    outputs = az_json(
        "deployment", "group", "show",
        "--resource-group", resource_group,
        "--name", DEPLOYMENT_NAME,
        "--query", "properties.outputs",
    )  # fmt: skip
    if not outputs:
        raise AzError(f"No deployment named {DEPLOYMENT_NAME!r} in {resource_group}.")
    return {name: output["value"] for name, output in outputs.items()}
