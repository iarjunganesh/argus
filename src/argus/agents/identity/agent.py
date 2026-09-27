"""
ARGUS Identity Agent
Verifies entity identity via registry lookups and document OCR.
"""

from argus.agents.identity.tools.customer_lookup import customer_lookup
from argus.agents.identity.tools.identity_validator import identity_validator
from argus.agents.identity.tools.ocr_processor import ocr_processor
from argus.agents.provenance import provenance
from argus.utils.structured_logger import get_logger

logger = get_logger("agent.identity")


async def assess(request: dict, task_id: str) -> dict:
    entity_name = request.get("entity_name", "")
    entity_type = request.get("entity_type", "individual")
    reg_number = request.get("registration_number")
    documents = request.get("documents", [])  # list of base64 doc images

    logger.info("assess", extra={"task_id": task_id, "entity": entity_name})

    # Step 1: Registry lookup
    registry_result = await customer_lookup(entity_name, entity_type, reg_number)

    # Step 2: OCR if documents provided
    ocr_results = []
    for doc in documents:
        ocr_result = await ocr_processor(
            doc.get("image_base64", ""),
            doc.get("doc_type", "passport"),
        )
        ocr_results.append(ocr_result)

    # Step 3: Cross-validate
    validation = await identity_validator(registry_result, ocr_results)

    identity_score = validation.get("confidence_score", 50)
    logger.info("assess.completed", extra={"task_id": task_id, "identity_score": identity_score})

    return {
        "agent": "identity",
        "task_id": task_id,
        "status": "completed",
        **provenance(
            customer_lookup=registry_result,
            **{f"ocr_processor[{i}]": r for i, r in enumerate(ocr_results)},
        ),
        "result": {
            "registry_match": registry_result.get("found", False),
            "ocr_documents": len(ocr_results),
            "discrepancies": validation.get("discrepancies", []),
            "identity_score": identity_score,
            "verified_fields": validation.get("verified_fields", []),
        },
    }
