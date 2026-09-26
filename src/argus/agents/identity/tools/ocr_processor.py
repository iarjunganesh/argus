"""
ocr_processor — reads structured fields from identity documents through the data plane's OCR.
With no OCR service available, the document counts as unread: no fields, labelled `fallback`.
"""

import base64
import binascii

from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.ocr_processor")


async def ocr_processor(image_base64: str, doc_type: str = "passport") -> dict:
    if not image_base64:
        return {"doc_type": doc_type, "fields": {}, "confidence": 0.0, "error": "No image provided"}
    try:
        image = base64.b64decode(image_base64, validate=True)
    except binascii.Error:
        return {"doc_type": doc_type, "fields": {}, "confidence": 0.0, "error": "Not base64"}

    plane = get_data_plane()
    try:
        fields = await plane.ocr.extract(image, doc_type)
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "ocr_processor", "reason": str(exc)})
        return {"doc_type": doc_type, "fields": {}, "confidence": 0.0, "source": "fallback"}

    confidence = min((f.get("confidence") or 0.0 for f in fields.values()), default=0.0)
    return {
        "doc_type": doc_type,
        "fields": fields,
        "confidence": confidence,
        "source": plane.backend,
    }
