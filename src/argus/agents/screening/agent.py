"""
ARGUS Screening Agent
Screens entities against sanctions, adverse media, and PEP databases.
sanctions_checker and adverse_media_scanner search the knowledge bases in the data plane.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from argus.agents.provenance import demo_provenance, provenance
from argus.agents.screening.tools.adverse_media_scanner import adverse_media_scanner
from argus.agents.screening.tools.pep_checker import pep_checker
from argus.agents.screening.tools.sanctions_checker import sanctions_checker
from argus.utils.demo_profiles import get_demo_profile
from argus.utils.env_loader import load_repo_env
from argus.utils.structured_logger import get_logger

load_repo_env(__file__)
app = FastAPI(title="ARGUS Screening Agent")
logger = get_logger("agent.screening")


class A2AMessage(BaseModel):
    a2a_version: str
    source_agent: str
    target_agent: str
    task_id: str
    payload: dict


@app.post("/a2a/invoke")
async def invoke(message: A2AMessage):
    payload = message.payload
    entity_name = payload.get("entity_name", "")
    aliases = payload.get("aliases", [])
    nationality = payload.get("nationality", "")
    dob_or_inc = payload.get("dob_or_incorporated", "")
    entity_type = payload.get("entity_type", "individual")
    jurisdiction = payload.get("jurisdiction", "")

    logger.info("invoke", extra={"task_id": message.task_id, "entity": entity_name})
    demo_profile = get_demo_profile(entity_name, entity_type, jurisdiction)
    if demo_profile and demo_profile.get("screening"):
        return {
            "agent": "screening",
            "task_id": message.task_id,
            "status": "completed",
            **demo_provenance(),
            "result": demo_profile["screening"],
        }

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
        "task_id": message.task_id,
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "screening", "version": "0.1.0"}
