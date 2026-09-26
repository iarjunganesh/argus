"""sanctions_checker — searches the sanctions knowledge base for the entity and its aliases."""

from argus.agents.screening.tools.name_match import mentions
from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.sanctions_checker")

MATCH_THRESHOLD = 0.2  # minimum retrieval score, 0 to 1, that counts as a match


async def sanctions_checker(entity_name: str, aliases: list[str], nationality: str) -> dict:
    # Names only: a nationality in the query would match every listing from that country.
    names = [entity_name, *aliases]
    query = " ".join(names)
    plane = get_data_plane()
    try:
        passages = await plane.retriever.search("sanctions", query, top=5)
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "sanctions_checker", "reason": str(exc)})
        return {"hit": False, "findings": [], "source": "fallback"}

    findings = [
        {
            "type": "sanctions",
            "match": p.content[:200],
            "confidence": p.score,
            "citation": {
                "knowledge_base": "sanctions",
                "document": p.source_doc,
                "snippet_id": p.id,
                "program": p.metadata.get("program"),
                "is_active": p.metadata.get("is_active"),
            },
        }
        for p in passages
        if p.score >= MATCH_THRESHOLD and mentions(f"{p.title} {p.content}", names)
    ]
    return {"hit": bool(findings), "findings": findings, "source": plane.backend}
