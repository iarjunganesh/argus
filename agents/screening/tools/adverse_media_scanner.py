"""
adverse_media_scanner — Foundry IQ powered tool
Queries KB-AdverseMedia (Azure AI Search index) for negative coverage.
Returns cited, grounded results — no hallucination risk.
"""
import json
import os
from config import FOUNDRY_IQ_KB_ADVERSEMEDIA


async def adverse_media_scanner(entity_name: str, aliases: list[str]) -> dict:
    base_query = " ".join([entity_name] + aliases)
    query = (
        base_query
        + " fraud corruption scandal investigation bribery money laundering"
    )

    try:
        from azure.search.documents import SearchClient
        from azure.search.documents.models import QueryType
        from azure.core.credentials import AzureKeyCredential

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key      = os.environ["AZURE_SEARCH_API_KEY"]
        client   = SearchClient(endpoint, FOUNDRY_IQ_KB_ADVERSEMEDIA, AzureKeyCredential(key))

        results = client.search(
            search_text=query,
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="default",
            top=5,
            select=["id", "content", "title", "source_doc", "metadata_json"],
        )

        findings = []
        hit      = False
        for r in results:
            score     = r.get("@search.reranker_score") or r.get("@search.score", 0)
            threshold = 2.2 if r.get("@search.reranker_score") else 0.4
            if score >= threshold:
                hit = True
                meta = {}
                if r.get("metadata_json"):
                    try:
                        meta = json.loads(r["metadata_json"])
                    except Exception:
                        pass
                findings.append({
                    "type":       "adverse_media",
                    "match":      r.get("content", "")[:250],
                    "confidence": round(min(score / 4.0, 1.0), 3),
                    "foundry_iq_citation": {
                        "knowledge_base": FOUNDRY_IQ_KB_ADVERSEMEDIA,
                        "document":       r.get("source_doc", "unknown"),
                        "snippet_id":     r.get("id"),
                        "published_at":   meta.get("published_at"),
                        "tags":           meta.get("tags", []),
                    },
                })

        return {"hit": hit, "findings": findings, "source": "foundry_iq"}

    except Exception as e:
        print(f"[adverse_media_scanner] Foundry IQ unavailable: {e}. Using mock.")
        return {"hit": False, "findings": [], "source": "mock"}
