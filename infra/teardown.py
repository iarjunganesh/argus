"""Remove an ARGUS deployment: everything in its resource group, then what Azure keeps afterwards.

usage: uv run python infra/teardown.py --resource-group RG          (dry run: lists only)
       uv run python infra/teardown.py --resource-group RG --yes    (deletes)

A dry run lists the resources that would go. With --yes it
  1. deletes the Log Analytics workspaces for good (a plain delete keeps them recoverable for
     14 days),
  2. deletes the resource group and everything in it, and waits,
  3. purges the soft-deleted AI Services and Document Intelligence accounts, which otherwise keep
     their names and model quota for 48 hours.
Cosmos DB and AI Search have no soft delete. The resource group must hold only ARGUS: every
resource in it is deleted.
"""

from __future__ import annotations

import argparse
import sys

from azcli import AzError, az, az_json

WORKSPACE = "Microsoft.OperationalInsights/workspaces"
COGNITIVE = "Microsoft.CognitiveServices/accounts"


def resources(resource_group: str) -> list[dict[str, str]]:
    return az_json(
        "resource", "list",
        "--resource-group", resource_group,
        "--query", "[].{name:name, type:type, location:location}",
    )  # fmt: skip


def delete(resource_group: str, found: list[dict[str, str]]) -> None:
    for r in found:
        if r["type"] == WORKSPACE:
            print(f"Deleting workspace {r['name']} without recovery...")
            az(
                "monitor", "log-analytics", "workspace", "delete",
                "--resource-group", resource_group,
                "--workspace-name", r["name"],
                "--force", "--yes",
            )  # fmt: skip
    print(f"Deleting resource group {resource_group} (this takes several minutes)...")
    az("group", "delete", "--name", resource_group, "--yes")
    for r in found:
        if r["type"] == COGNITIVE:
            print(f"Purging {r['name']}...")
            az(
                "cognitiveservices", "account", "purge",
                "--resource-group", resource_group,
                "--name", r["name"],
                "--location", r["location"],
            )  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--yes", action="store_true", help="delete; without it, only list")
    args = parser.parse_args(argv)

    try:
        found = resources(args.resource_group)
        print(f"{len(found)} resources in {args.resource_group}:")
        for r in sorted(found, key=lambda r: (r["type"], r["name"])):
            print(f"  {r['type']:55} {r['name']}")
        if not args.yes:
            print("\nDry run: nothing was deleted. Add --yes to delete all of the above.")
            return 0
        delete(args.resource_group, found)
    except AzError as exc:
        print(exc)
        return 1
    print("Done: the resource group is gone and the AI accounts are purged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
