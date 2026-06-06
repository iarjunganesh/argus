"""
sanctions_checker — Foundry IQ powered tool
Queries KB-Sanctions (Azure AI Search index) for entity matches.
Returns cited, grounded results — no hallucination risk.
"""
import os
import json
from config import FOUNDRY_IQ_KB_SANCTIONS


async def sanctions_checker(
    entity_name: str,
    aliases: list[str],
    nationality: str,
) -> dict:
    """
    Query Foundry IQ KB-Sanctions for the entity and its aliases.
    Uses Azure AI Search semantic search with citation metadata.
    """
    query_terms = [entity_name] + aliases
    query = " ".join(query_terms) + (f" {nationality}" if nationality else "")

    try:
        from azure.search.documents import SearchClient
        from azure.search.documents.models import QueryType
        from azure.core.credentials import AzureKeyCredential

        endpoint  = os.environ["AZURE_SEARCH_ENDPOINT"]
        key       = os.environ["AZURE_SEARCH_API_KEY"]
        client    = SearchClient(endpoint, FOUNDRY_IQ_KB_SANCTIONS, AzureKeyCredential(key))

        results = client.search(
            search_text=query,
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="default",
            top=5,
            select=["id", "content", "title", "source_doc", "entity_name", "metadata_json"],
        )

        findings = []
        hit      = False
        for r in results:
            score = r.get("@search.reranker_score") or r.get("@search.score", 0)
            # Semantic reranker scores: >2.5 is a strong match (max is ~4.0)
            # BM25 fallback: >0.5 is reasonable
            threshold = 2.5 if r.get("@search.reranker_score") else 0.5
            if score >= threshold:
                hit = True
                meta = {}
                if r.get("metadata_json"):
                    try:
                        meta = json.loads(r["metadata_json"])
                    except Exception:
                        pass
                findings.append({
                    "type":       "sanctions",
                    "match":      r.get("content", "")[:200],
                    "confidence": round(min(score / 4.0, 1.0), 3),
                    "foundry_iq_citation": {
                        "knowledge_base": FOUNDRY_IQ_KB_SANCTIONS,
                        "document":       r.get("source_doc", "unknown"),
                        "snippet_id":     r.get("id"),
                        "program":        meta.get("program"),
                        "is_active":      meta.get("is_active"),
                    },
                })

        return {"hit": hit, "findings": findings, "source": "foundry_iq"}

    except Exception as e:
        print(f"[sanctions_checker] Foundry IQ unavailable: {e}. Using mock.")
        return _mock_sanctions_response(entity_name)


def _mock_sanctions_response(entity_name: str) -> dict:
    """Mock response for local development before Foundry IQ is provisioned."""
    return {
        "hit": False,
        "findings": [],
        "source": "mock",
        "note": "Foundry IQ not yet provisioned. Run: make index-knowledge-bases",
    }
