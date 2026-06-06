"""identity_validator — Cross-references OCR output against registry record."""

async def identity_validator(registry_result: dict, ocr_results: list[dict]) -> dict:
    record = registry_result.get("record") or {}
    discrepancies = []
    verified_fields = []

    for ocr in ocr_results:
        fields = ocr.get("fields", {})

        # Name check
        ocr_name = (fields.get("full_name") or fields.get("entity_name") or {}).get("value", "")
        reg_name  = record.get("name", "")
        if ocr_name and reg_name:
            if ocr_name.lower().strip() == reg_name.lower().strip():
                verified_fields.append("name")
            else:
                discrepancies.append({
                    "field":    "name",
                    "registry": reg_name,
                    "document": ocr_name,
                    "severity": "high",
                })

        # DOB check (individuals)
        ocr_dob = (fields.get("date_of_birth") or {}).get("value", "")
        reg_dob  = record.get("date_of_birth", "")
        if ocr_dob and reg_dob:
            if ocr_dob == reg_dob:
                verified_fields.append("date_of_birth")
            else:
                discrepancies.append({
                    "field":    "date_of_birth",
                    "registry": reg_dob,
                    "document": ocr_dob,
                    "severity": "medium",
                })

    # Confidence score: penalise discrepancies
    high_count   = sum(1 for d in discrepancies if d["severity"] == "high")
    medium_count = sum(1 for d in discrepancies if d["severity"] == "medium")
    confidence   = max(0, 100 - (high_count * 30) - (medium_count * 10))

    return {
        "verified_fields":  verified_fields,
        "discrepancies":    discrepancies,
        "confidence_score": confidence,
    }
