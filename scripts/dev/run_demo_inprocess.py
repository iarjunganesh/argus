"""Run one ARGUS assessment in this process and print the report.

A quick end-to-end smoke test: no API server or UI needed.
"""

import asyncio
import json

from argus.agents.orchestrator import agent as orchestrator


async def main():
    # Example KYC request — canonical demo profile key
    kyc = {"entity_name": "Wirecard AG", "entity_type": "corporate", "jurisdiction": "DE"}
    print("Running in-process KYC assessment for:", kyc)
    report = await orchestrator.run_kyc_assessment(kyc)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
