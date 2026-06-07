"""Create and seed the Azure AI Search typology index used by the transaction agent."""
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchableField,
    SimpleField,
    SearchFieldDataType,
)

load_dotenv()

INDEX_NAME = "argus-typologies-index"

TYPOLOGY_DOCS = [
    {
        "id": "typology-structuring",
        "typology_name": "Structuring / Smurfing",
        "description": "Multiple transactions are deliberately placed below reporting thresholds to avoid AML detection controls.",
        "fatf_reference": "FATF Typologies Report 2023 — Structuring",
    },
    {
        "id": "typology-layering",
        "typology_name": "Layering via multiple counterparties",
        "description": "Funds are moved rapidly across several counterparties or accounts to obscure the original source and ownership trail.",
        "fatf_reference": "FATF Typologies Report 2023 — Layering",
    },
    {
        "id": "typology-rapid-movement",
        "typology_name": "Rapid movement of funds",
        "description": "Unusually quick transfers across accounts and jurisdictions can indicate attempts to break auditability and frustrate due diligence.",
        "fatf_reference": "FATF Red Flag Indicators — Rapid Movement",
    },
]


def create_typology_index() -> None:
    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    key = os.environ["AZURE_SEARCH_API_KEY"]
    credential = AzureKeyCredential(key)

    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    search_client = SearchClient(endpoint=endpoint, index_name=INDEX_NAME, credential=credential)

    index = SearchIndex(
        name=INDEX_NAME,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SearchableField(name="typology_name", type=SearchFieldDataType.String),
            SearchableField(name="description", type=SearchFieldDataType.String),
            SearchableField(name="fatf_reference", type=SearchFieldDataType.String),
        ],
    )

    try:
        index_client.create_or_update_index(index)
    except HttpResponseError as exc:
        if "Maximum number of indexes allowed" in str(exc):
            print(
                "Typology index could not be created because the current Azure AI Search tier allows only 3 indexes. "
                "ARGUS will use the live regulations KB as the typology search fallback instead."
            )
            return
        raise

    result = search_client.upload_documents(TYPOLOGY_DOCS)
    succeeded = sum(1 for item in result if item.succeeded)
    print(f"Typology index ready: {INDEX_NAME} ({succeeded}/{len(TYPOLOGY_DOCS)} docs uploaded)")


if __name__ == "__main__":
    create_typology_index()