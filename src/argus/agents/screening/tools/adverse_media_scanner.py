"""adverse_media_scanner — searches the adverse media knowledge base for negative coverage."""

from argus.agents.screening.tools.name_match import mentions
from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.adverse_media_scanner")

MATCH_THRESHOLD = 0.2  # minimum retrieval score, 0 to 1, that counts as a match


async def adverse_media_scanner(entity_name: str, aliases: list[str]) -> dict:
    # The knowledge base holds only negative coverage, so the query is the names alone.
    names = [entity_name, *aliases]
    query = " ".join(names)
    plane = get_data_plane()
    try:
        passages = await plane.retriever.search("adverse_media", query, top=5)
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "adverse_media_scanner", "reason": str(exc)})
        return {"hit": False, "findings": [], "source": "fallback"}

    findings = [
        {
            "type": "adverse_media",
            "match": p.content[:250],
            "confidence": p.score,
            "citation": {
                "knowledge_base": "adverse_media",
                "document": p.source_doc,
                "snippet_id": p.id,
                "published_at": p.metadata.get("published_at"),
                "tags": p.metadata.get("tags", []),
            },
        }
        for p in passages
        if p.score >= MATCH_THRESHOLD and mentions(f"{p.title} {p.content}", names)
    ]
    return {"hit": bool(findings), "findings": findings, "source": plane.backend}
