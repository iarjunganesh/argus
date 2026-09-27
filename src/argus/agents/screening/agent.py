"""
ARGUS Screening Agent
Screens entities against sanctions, adverse media, and PEP databases.
sanctions_checker and adverse_media_scanner search the knowledge bases in the data plane.
"""

from argus.agents.provenance import provenance
from argus.agents.screening.tools.adverse_media_scanner import adverse_media_scanner
from argus.agents.screening.tools.pep_checker import pep_checker
from argus.agents.screening.tools.sanctions_checker import sanctions_checker
from argus.utils.structured_logger import get_logger

logger = get_logger("agent.screening")


async def assess(request: dict, task_id: str) -> dict:
    entity_name = request.get("entity_name", "")
    aliases = request.get("aliases", [])
    nationality = request.get("nationality", "")
    dob_or_inc = request.get("dob_or_incorporated", "")

    logger.info("assess", extra={"task_id": task_id, "entity": entity_name})

    # Run all three screening tools
    sanctions_result = await sanctions_checker(entity_name, aliases, nationality)
    adverse_media_result = await adverse_media_scanner(entity_name, aliases)
    pep_result = await pep_checker(entity_name, dob_or_inc, nationality)

    # Aggregate findings
    all_findings = (
        sanctions_result.get("findings", [])
        + adverse_media_result.get("findings", [])
        + pep_result.get("findings", [])
    )

    # Compute screening risk score (0-100)
    base_score = 0
    if sanctions_result.get("hit"):
        base_score += 60
    if pep_result.get("hit"):
        base_score += 25
    if adverse_media_result.get("hit"):
        base_score += 15
    screening_risk_score = min(base_score, 100)

    return {
        "agent": "screening",
        "task_id": task_id,
        "status": "completed",
        **provenance(
            sanctions_checker=sanctions_result,
            adverse_media_scanner=adverse_media_result,
            pep_checker=pep_result,
        ),
        "result": {
            "sanctions_hit": sanctions_result.get("hit", False),
            "adverse_media_hit": adverse_media_result.get("hit", False),
            "pep_hit": pep_result.get("hit", False),
            "findings": all_findings,
            "screening_risk_score": screening_risk_score,
            # Knowledge-base searches that answered (sanctions and adverse media).
            "retrieval_queries": sum(
                r.get("source") != "fallback" for r in (sanctions_result, adverse_media_result)
            ),
        },
    }
