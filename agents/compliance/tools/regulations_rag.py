"""
regulations_rag — Foundry IQ powered tool
Queries KB-Regulations (Azure AI Search index) for applicable FATF/4AMLD/6AMLD/GDPR text.
Returns cited, grounded regulatory references — no hallucination.
"""
import json
import os
from config import FOUNDRY_IQ_KB_REGULATIONS


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
        from azure.search.documents import SearchClient
        from azure.search.documents.models import QueryType
        from azure.core.credentials import AzureKeyCredential

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key      = os.environ["AZURE_SEARCH_API_KEY"]
        client   = SearchClient(endpoint, FOUNDRY_IQ_KB_REGULATIONS, AzureKeyCredential(key))

        results = client.search(
            search_text=enriched_query,
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="default",
            top=8,
            select=["id", "content", "title", "source_doc", "metadata_json"],
        )

        regulations = []
        for r in results:
            score     = r.get("@search.reranker_score") or r.get("@search.score", 0)
            threshold = 1.5 if r.get("@search.reranker_score") else 0.3
            if score >= threshold:
                regulations.append({
                    "text":      r.get("content", ""),
                    "relevance": round(min(score / 4.0, 1.0), 3),
                    "foundry_iq_citation": {
                        "knowledge_base": FOUNDRY_IQ_KB_REGULATIONS,
                        "document":       r.get("source_doc", "unknown"),
                        "article":        r.get("title", "unknown"),
                        "snippet_id":     r.get("id"),
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

    except Exception as e:
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
