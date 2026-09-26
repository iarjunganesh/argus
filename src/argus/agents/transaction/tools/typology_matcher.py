"""typology_matcher — matches detected patterns to money-laundering typologies.

Searches the regulations knowledge base for guidance on each detected pattern. When nothing is
retrieved, it names the pattern from ARGUS's own rules and cites no document, rather than
inventing a reference.
"""

from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.typology_matcher")

MATCH_THRESHOLD = 0.2  # minimum retrieval score, 0 to 1, that counts as a match


async def typology_matcher(patterns: dict) -> list:
    query_parts = []
    if patterns.get("structuring_flag"):
        query_parts.append("structuring smurfing cash threshold")
    if patterns.get("layering_flag"):
        query_parts.append("layering multiple counterparties rapid movement")
    if not query_parts:
        return []

    try:
        passages = await get_data_plane().retriever.search(
            "regulations", " ".join(query_parts), top=3
        )
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "typology_matcher", "reason": str(exc)})
        passages = []

    hits = [
        {
            "typology": p.title[:80] or "Regulatory typology guidance",
            "description": p.content[:150],
            "fatf_ref": p.source_doc,
            "score": p.score,
            "source": "retrieved",
        }
        for p in passages
        if p.score >= MATCH_THRESHOLD
    ]
    return hits or _rule_typology_hits(patterns)


def _rule_typology_hits(patterns: dict) -> list:
    """The pattern names ARGUS's rules detected, without a document reference."""
    hits = []
    if patterns.get("structuring_flag"):
        hits.append(
            {
                "typology": "Structuring / Smurfing",
                "description": (
                    "Multiple transactions structured below reporting threshold to avoid detection."
                ),
                "fatf_ref": "",
                "score": 1.0,
                "source": "rules",
            }
        )
    if patterns.get("layering_flag"):
        hits.append(
            {
                "typology": "Layering via multiple counterparties",
                "description": (
                    "Rapid movement of funds through numerous accounts to obscure origin."
                ),
                "fatf_ref": "",
                "score": 1.0,
                "source": "rules",
            }
        )
    return hits
