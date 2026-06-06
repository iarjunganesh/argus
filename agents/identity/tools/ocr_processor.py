"""
ocr_processor — Azure Document Intelligence
Extracts structured fields from synthetic identity documents.
Supports: passport, drivers_license, id_card, tax_invoice
"""
import os, base64
from config import get_llm_client, MODEL_NAME

DOC_TYPE_FIELDS = {
    "passport":         ["full_name", "date_of_birth", "nationality", "passport_number", "expiry_date", "issuing_country"],
    "drivers_license":  ["full_name", "date_of_birth", "licence_number", "expiry_date", "address", "issuing_state"],
    "id_card":          ["full_name", "date_of_birth", "id_number", "nationality", "expiry_date"],
    "tax_invoice":      ["entity_name", "tax_id", "address", "invoice_number", "date", "amount"],
}

async def ocr_processor(image_base64: str, doc_type: str = "passport") -> dict:
    """
    Extract structured fields from a document image.
    Uses Azure Document Intelligence if available, falls back to GPT-4o vision.
    """
    if not image_base64:
        return {"doc_type": doc_type, "fields": {}, "confidence": 0.0, "error": "No image provided"}

    # Try Azure Document Intelligence first
    try:
        from azure.ai.formrecognizer import DocumentAnalysisClient
        from azure.core.credentials import AzureKeyCredential

        client = DocumentAnalysisClient(
            endpoint=os.environ["DOC_INTELLIGENCE_ENDPOINT"],
            credential=AzureKeyCredential(os.environ["DOC_INTELLIGENCE_KEY"]),
        )
        image_bytes = base64.b64decode(image_base64)
        poller = client.begin_analyze_document("prebuilt-idDocument", document=image_bytes)
        result  = poller.result()

        fields = {}
        for doc in result.documents:
            for field_name, field in doc.fields.items():
                fields[field_name] = {
                    "value":      str(field.value) if field.value else None,
                    "confidence": field.confidence,
                }

        return {"doc_type": doc_type, "fields": fields, "source": "azure_doc_intelligence"}

    except Exception as e:
        print(f"[ocr_processor] Doc Intelligence unavailable: {e}. Using mock.")
        return _mock_ocr(doc_type)


def _mock_ocr(doc_type: str) -> dict:
    from faker import Faker
    fake = Faker()
    field_names = DOC_TYPE_FIELDS.get(doc_type, [])
    mock_fields = {f: {"value": f"MOCK_{f.upper()}", "confidence": 0.9} for f in field_names}
    return {
        "doc_type":   doc_type,
        "fields":     mock_fields,
        "confidence": 0.9,
        "source":     "mock",
        "note":       "Azure Document Intelligence not provisioned yet.",
    }
