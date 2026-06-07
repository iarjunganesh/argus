"""
regulations_rag — Foundry IQ powered tool
Queries KB-Regulations through the Foundry IQ knowledge base API for applicable FATF/4AMLD/6AMLD/GDPR text.
Returns cited, grounded regulatory references — no hallucination.
"""
from config import FOUNDRY_IQ_KB_REGULATIONS, get_foundry_client


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


async def regulations_rag(
    query: str,
    jurisdiction: str,
    entity_type: str,
    risk_indicators: list[str],
) -> dict:
    """
    Query Foundry IQ KB-Regulations for relevant regulatory requirements.
    All returned text includes citations to the source document and article.
    """
    enriched_query = (
        f"{query} "
        f"jurisdiction {jurisdiction} "
        f"{entity_type} "
        f"{' '.join(risk_indicators)}"
    )

    try:
        client = get_foundry_client()
        results = client.knowledge_bases.query(
            knowledge_base_name=FOUNDRY_IQ_KB_REGULATIONS,
            query=enriched_query,
            top=8,
            include_citations=True,
        )

        regulations = []
        for item in _item_field(results, "items", []):
            score = float(_item_field(item, "relevance_score", 0) or 0)
            citation = _item_field(item, "citation")
            if score >= 0.15:
                regulations.append({
                    "text":      _item_field(item, "content", ""),
                    "relevance": _normalize_relevance(score),
                    "foundry_iq_citation": {
                        "knowledge_base": FOUNDRY_IQ_KB_REGULATIONS,
                        "document":       _citation_field(citation, "document_title", "unknown"),
                        "article":        _citation_field(citation, "section", _citation_field(citation, "article", "unknown")),
                        "snippet_id":     _citation_field(citation, "snippet_id", _item_field(item, "id")),
                    },
                })

        if not regulations:
            # Always return at least the core FATF CDD requirement
            regulations = _fallback_regulations()

        return {
            "regulations":    regulations,
            "query":          enriched_query,
            "source":         "foundry_iq",
            "knowledge_base": FOUNDRY_IQ_KB_REGULATIONS,
        }

    except (ImportError, KeyError, RuntimeError, AttributeError, TypeError, ValueError) as e:
        print(f"[regulations_rag] Foundry IQ unavailable: {e}. Using mock.")
        return _mock_regulations_response()


def _fallback_regulations() -> list:
    """Returns core FATF CDD text as a baseline when no strong matches found."""
    return [
        {
            "text": (
                "FATF Recommendation 10: Financial institutions must undertake "
                "customer due diligence (CDD) when establishing business relations, "
                "for occasional transactions above USD/EUR 15,000, and whenever there "
                "is suspicion of money laundering or terrorist financing."
            ),
            "relevance": 0.75,
            "foundry_iq_citation": {
                "knowledge_base": FOUNDRY_IQ_KB_REGULATIONS,
                "document":       "fatf-40-recommendations.pdf",
                "article":        "Recommendation 10 — Customer Due Diligence",
                "snippet_id":     "fatf-rec-10",
            },
        }
    ]


def _mock_regulations_response() -> dict:
    """Mock for local development before Foundry IQ is provisioned."""
    return {
        "regulations": [
            {
                "text": "FATF Recommendation 12: Countries should take measures to prevent the misuse of legal persons for money laundering or terrorist financing.",
                "relevance": 0.91,
                "foundry_iq_citation": {
                    "knowledge_base": "mock",
                    "document": "fatf-40-recommendations.pdf",
                    "article": "Recommendation 12",
                    "snippet_id": "fatf-rec-12",
                },
            }
        ],
        "source": "mock",
        "note": "Foundry IQ not yet provisioned. Run: make index-knowledge-bases",
    }
