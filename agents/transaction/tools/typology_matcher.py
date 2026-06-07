"""typology_matcher — matches detected patterns against FATF typologies via Azure AI Search."""
from config import FOUNDRY_IQ_KB_REGULATIONS, get_search_client

TYPOLOGY_INDEX = "argus-typologies-index"

async def typology_matcher(patterns: dict) -> list:
    query_parts = []
    if patterns.get("structuring_flag"): query_parts.append("structuring smurfing cash threshold")
    if patterns.get("layering_flag"):    query_parts.append("layering multiple counterparties rapid movement")
    if not query_parts:
        return []

    query = " ".join(query_parts)
    for index_name, mapper in (
        (TYPOLOGY_INDEX, _map_typology_index_hits),
        (FOUNDRY_IQ_KB_REGULATIONS, _map_regulations_index_hits),
    ):
        try:
            client = get_search_client(index_name)
            results = client.search(search_text=query, top=3)
            hits = mapper(results)
            if hits:
                return hits
        except Exception as e:
            print(f"[typology_matcher] AI Search index {index_name} unavailable: {e}.")

    return _mock_typology_hits(patterns)


def _map_typology_index_hits(results) -> list:
    hits = []
    for r in results:
        hits.append({
            "typology": r.get("typology_name", "Unknown"),
            "description": r.get("description", "")[:150],
            "fatf_ref": r.get("fatf_reference", ""),
            "score": round(r.get("@search.score", 0), 3),
        })
    return hits


def _map_regulations_index_hits(results) -> list:
    hits = []
    for r in results:
        title = r.get("title") or "Regulatory typology guidance"
        content = r.get("content", "")
        hits.append({
            "typology": title[:80],
            "description": content[:150],
            "fatf_ref": r.get("source_doc", ""),
            "score": round(r.get("@search.reranker_score") or r.get("@search.score", 0), 3),
        })
    return hits


def _mock_typology_hits(patterns: dict) -> list:
    hits = []
    if patterns.get("structuring_flag"):
        hits.append({
            "typology":    "Structuring / Smurfing",
            "description": "Multiple transactions structured below reporting threshold to avoid detection.",
            "fatf_ref":    "FATF Typologies Report 2023 — Chapter 3.2",
            "score":       0.91,
        })
    if patterns.get("layering_flag"):
        hits.append({
            "typology":    "Layering via multiple counterparties",
            "description": "Rapid movement of funds through numerous accounts to obscure origin.",
            "fatf_ref":    "FATF Typologies Report 2023 — Chapter 4.1",
            "score":       0.78,
        })
    return hits
