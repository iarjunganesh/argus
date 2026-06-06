"""typology_matcher — matches detected patterns against FATF typologies via Azure AI Search."""
from config import get_search_client

TYPOLOGY_INDEX = "argus-typologies-index"

async def typology_matcher(patterns: dict) -> list:
    query_parts = []
    if patterns.get("structuring_flag"): query_parts.append("structuring smurfing cash threshold")
    if patterns.get("layering_flag"):    query_parts.append("layering multiple counterparties rapid movement")
    if not query_parts:
        return []

    query = " ".join(query_parts)
    try:
        client  = get_search_client(TYPOLOGY_INDEX)
        results = client.search(search_text=query, top=3)
        hits = []
        for r in results:
            hits.append({
                "typology":    r.get("typology_name", "Unknown"),
                "description": r.get("description", "")[:150],
                "fatf_ref":    r.get("fatf_reference", ""),
                "score":       round(r.get("@search.score", 0), 3),
            })
        return hits
    except Exception as e:
        print(f"[typology_matcher] AI Search unavailable: {e}. Using mock.")
        return _mock_typology_hits(patterns)


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
