"""Fill a deployed ARGUS data plane with the synthetic data and the regulation texts.

usage: uv run python infra/populate.py --resource-group RG

Run once after the first deployment (docs/DEPLOYMENT.md), and again after regenerating the data;
every step overwrites what is there. It needs `az login` as the operator that infra/main.bicep
was given as `operatorPrincipalId` (for the Cosmos DB data role), and generated synthetic data in
data/synthetic/ (run its generate_*.py scripts first).

Steps, each a script that also runs on its own:
  1. infra/foundry_iq/create_knowledge_bases.py   indexes, knowledge sources, knowledge bases
  2. infra/foundry_iq/index_regulations.py        the regulation texts
  3. data/public/generate_adverse_media_public.py  the public-source demo articles
  4. infra/foundry_iq/index_sanctions_and_media.py sanctions and adverse media
  5. data/synthetic/upload_to_cosmos.py           entities, ownership, transactions

The search admin key is read with the operator's Azure access and handed to the steps in their
environment only. The steps ignore `.env` (ARGUS_DISABLE_DOTENV), so they reach exactly the
deployment named here.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from azcli import AzError, az, deployment_outputs

ROOT = Path(__file__).resolve().parents[1]
STEPS = (
    "infra/foundry_iq/create_knowledge_bases.py",
    "infra/foundry_iq/index_regulations.py",
    "data/public/generate_adverse_media_public.py",
    "infra/foundry_iq/index_sanctions_and_media.py",
    "data/synthetic/upload_to_cosmos.py",
)
SYNTHETIC = ("entities", "corporate_graph", "transactions", "sanctions", "adverse_media")


def step_environment(resource_group: str) -> dict[str, str]:
    outputs = deployment_outputs(resource_group)
    search = outputs["searchName"]
    admin_key = az(
        "search", "admin-key", "show",
        "--resource-group", resource_group,
        "--service-name", search,
        "--query", "primaryKey",
        "--output", "tsv",
    )  # fmt: skip
    return {
        **os.environ,
        "ARGUS_DISABLE_DOTENV": "1",
        "AZURE_SEARCH_ENDPOINT": f"https://{search}.search.windows.net",
        "AZURE_SEARCH_API_KEY": admin_key,
        "COSMOS_ENDPOINT": outputs["cosmosEndpoint"],
        "COSMOS_DATABASE": outputs["cosmosDatabase"],
        "COSMOS_KEY": "",  # local authentication is off: sign in with Entra ID
        "PYTHONUTF8": "1",
    }


def missing_data() -> list[str]:
    folder = ROOT / "data" / "synthetic"
    return [name for name in SYNTHETIC if not (folder / f"{name}.jsonl").exists()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--resource-group", required=True)
    args = parser.parse_args(argv)

    if missing := missing_data():
        print(f"Generate the synthetic data first; missing: {', '.join(missing)}.")
        return 1
    try:
        env = step_environment(args.resource_group)
    except AzError as exc:
        print(exc)
        return 1
    for step in STEPS:
        print(f"\n── {step}")
        result = subprocess.run([sys.executable, str(ROOT / step)], env=env, check=False)  # noqa: S603 - fixed scripts
        if result.returncode != 0:
            print(f"{step} failed; the steps after it did not run.")
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
