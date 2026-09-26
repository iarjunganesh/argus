"""transaction_monitor — loads the entity's transaction history from the data plane."""

from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.transaction_monitor")


async def transaction_monitor(entity_name: str) -> dict:
    plane = get_data_plane()
    try:
        items = await plane.entities.transactions(entity_name, limit=500)
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "transaction_monitor", "reason": str(exc)})
        return {"count": 0, "transactions": [], "date_range": {}, "source": "fallback"}

    dates = [t["date"] for t in items if t.get("date")]
    return {
        "count": len(items),
        "transactions": items,
        "date_range": {"from": min(dates), "to": max(dates)} if dates else {},
        "source": plane.backend,
    }
