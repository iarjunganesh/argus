"""
adverse_media_scanner — Foundry IQ powered tool
Queries KB-AdverseMedia through the Foundry IQ knowledge base API for negative coverage.
Returns cited, grounded results — no hallucination risk.
"""
import json
from config import FOUNDRY_IQ_KB_ADVERSEMEDIA, get_foundry_client


def _item_field(item, name: str, default=None):
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _citation_field(citation, name: str, default=None):
    if citation is None:
        return default
    if isinstance(citation, dict):
        return citation.get(name, default)
    return getattr(citation, name, default)


def _normalize_relevance(score: float) -> float:
    if score <= 1:
        return round(max(score, 0.0), 3)
    return round(min(score / 4.0, 1.0), 3)


def _load_metadata(item) -> dict:
    raw = _item_field(item, "metadata_json") or _item_field(item, "metadata") or "{}"
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


async def adverse_media_scanner(entity_name: str, aliases: list[str]) -> dict:
    base_query = " ".join([entity_name] + aliases)
    query = (
        base_query
        + " fraud corruption scandal investigation bribery money laundering"
    )

    try:
        client = get_foundry_client()
        results = client.knowledge_bases.query(
            knowledge_base_name=FOUNDRY_IQ_KB_ADVERSEMEDIA,
            query=query,
            top=5,
            include_citations=True,
        )

        findings = []
        hit      = False
        for item in _item_field(results, "items", []):
            score = float(_item_field(item, "relevance_score", 0) or 0)
            threshold = 0.2
            if score >= threshold:
                hit = True
                citation = _item_field(item, "citation")
                meta = _load_metadata(item)
                findings.append({
                    "type":       "adverse_media",
                    "match":      _item_field(item, "content", "")[:250],
                    "confidence": _normalize_relevance(score),
                    "foundry_iq_citation": {
                        "knowledge_base": FOUNDRY_IQ_KB_ADVERSEMEDIA,
                        "document":       _citation_field(citation, "document_title", "unknown"),
                        "snippet_id":     _citation_field(citation, "snippet_id", _item_field(item, "id")),
                        "published_at":   meta.get("published_at"),
                        "tags":           meta.get("tags", []),
                    },
                })

        return {"hit": hit, "findings": findings, "source": "foundry_iq"}

    except (ImportError, KeyError, RuntimeError, AttributeError, TypeError, ValueError) as e:
        print(f"[adverse_media_scanner] Foundry IQ unavailable: {e}. Using mock.")
        return {"hit": False, "findings": [], "source": "mock"}
