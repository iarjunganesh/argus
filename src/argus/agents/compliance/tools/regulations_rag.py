"""
regulations_rag — searches the regulations knowledge base for the obligations that apply.
Every returned rule carries a citation to its source document and section.
"""

from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.regulations_rag")

MATCH_THRESHOLD = 0.15  # minimum retrieval score, 0 to 1, that counts as relevant


async def regulations_rag(
    query: str,
    jurisdiction: str,
    entity_type: str,
    risk_indicators: list[str],
) -> dict:
    enriched_query = (
        f"{query} jurisdiction {jurisdiction} {entity_type} {' '.join(risk_indicators)}"
    )
    plane = get_data_plane()
    try:
        passages = await plane.retriever.search("regulations", enriched_query, top=8)
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "regulations_rag", "reason": str(exc)})
        return {
            "regulations": _baseline_regulations(),
            "query": enriched_query,
            "source": "fallback",
        }

    regulations = [
        {
            "text": p.content,
            "relevance": p.score,
            "citation": {
                "knowledge_base": "regulations",
                "document": p.source_doc,
                "article": p.title,
                "snippet_id": p.id,
            },
        }
        for p in passages
        if p.score >= MATCH_THRESHOLD
    ]
    return {
        "regulations": regulations or _baseline_regulations(),
        "query": enriched_query,
        "source": plane.backend,
    }


def _baseline_regulations() -> list:
    """Core FATF customer due diligence text, used when nothing more specific is retrieved."""
    return [
        {
            "text": (
                "FATF Recommendation 10: Financial institutions must undertake "
                "customer due diligence (CDD) when establishing business relations, "
                "for occasional transactions above USD/EUR 15,000, and whenever there "
                "is suspicion of money laundering or terrorist financing."
            ),
            "relevance": 0.75,
            "citation": {
                "knowledge_base": "regulations",
                "document": "fatf-40-recommendations.pdf",
                "article": "Recommendation 10 — Customer Due Diligence",
                "snippet_id": "fatf-rec-10",
            },
        }
    ]
