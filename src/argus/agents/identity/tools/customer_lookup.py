"""customer_lookup — finds the entity in the registry held by the data plane."""

from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.customer_lookup")


async def customer_lookup(entity_name: str, entity_type: str, reg_number: str | None) -> dict:
    plane = get_data_plane()
    try:
        record = await plane.entities.find_entity(entity_name, entity_type)
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "customer_lookup", "reason": str(exc)})
        return {"found": False, "record": None, "source": "fallback"}
    return {"found": record is not None, "record": record, "source": plane.backend}
