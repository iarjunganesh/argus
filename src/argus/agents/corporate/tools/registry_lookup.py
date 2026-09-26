"""registry_lookup — finds the company in the corporate registry held by the data plane."""

from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.registry_lookup")


async def registry_lookup(entity_name: str, reg_number: str | None) -> dict:
    plane = get_data_plane()
    try:
        record = await plane.entities.find_entity(entity_name, "corporate")
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "registry_lookup", "reason": str(exc)})
        return {"found": False, "record": None, "source": "fallback"}
    return {"found": record is not None, "record": record, "source": plane.backend}
