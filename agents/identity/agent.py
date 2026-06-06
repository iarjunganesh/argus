"""
ARGUS Identity Agent
Verifies entity identity via registry lookups and document OCR.
"""
from fastapi import FastAPI
from utils.structured_logger import get_logger
from pydantic import BaseModel
from agents.identity.tools.customer_lookup import customer_lookup
from agents.identity.tools.ocr_processor import ocr_processor
from agents.identity.tools.identity_validator import identity_validator

app = FastAPI(title="ARGUS Identity Agent")
logger = get_logger('agent.identity')

class A2AMessage(BaseModel):
    a2a_version: str
    source_agent: str
    target_agent: str
    task_id: str
    payload: dict

@app.post("/a2a/invoke")
async def invoke(message: A2AMessage):
    p = message.payload
    entity_name = p.get("entity_name", "")
    entity_type = p.get("entity_type", "individual")
    reg_number  = p.get("registration_number")
    documents   = p.get("documents", [])   # list of base64 doc images

    logger.info('invoke', extra={"task_id": message.task_id, "entity": entity_name})
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
    logger.info('invoke.completed', extra={"task_id": message.task_id, "identity_score": identity_score})

    return {
        "agent":   "identity",
        "task_id": message.task_id,
        "status":  "completed",
        "result": {
            "registry_match":    registry_result.get("found", False),
            "ocr_documents":     len(ocr_results),
            "discrepancies":     validation.get("discrepancies", []),
            "identity_score":    identity_score,
            "verified_fields":   validation.get("verified_fields", []),
        },
    }


@app.get('/health')
def health():
    return {"status": "ok", "service": "identity", "version": "0.1.0"}
