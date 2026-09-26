"""
ubo_resolver — Recursive UBO graph traversal over the ownership graph in the data plane.
Stops at individuals with >25% ownership or at depth limit (5 levels).
"""

from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.ubo_resolver")

OWNERSHIP_THRESHOLD = 25.0  # FATF standard UBO threshold
MAX_DEPTH = 5


async def ubo_resolver(entity_name: str, registry_result: dict, depth: int = 0) -> dict:
    if depth >= MAX_DEPTH:
        return {"ubos": [], "ownership_chain": [], "depth": depth, "note": "Max depth reached"}

    plane = get_data_plane()
    try:
        nodes = await plane.entities.ownership_children(entity_name)
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "ubo_resolver", "reason": str(exc)})
        return {"ubos": [], "ownership_chain": [], "depth": depth, "source": "fallback"}

    ubos = []
    chain = []
    source: str = plane.backend
    for node in nodes:
        ownership_pct = node.get("ownership_percentage", 0)
        node_type = node.get("entity_type", "corporate")
        node_info = {
            "name": node.get("name"),
            "entity_type": node_type,
            "ownership_pct": ownership_pct,
            "jurisdiction": node.get("jurisdiction", ""),
            "depth": depth + 1,
        }
        chain.append(node_info)

        if node_type == "individual" and ownership_pct >= OWNERSHIP_THRESHOLD:
            ubos.append({**node_info, "is_ubo": True})
        elif node_type == "corporate":
            child = await ubo_resolver(node.get("name", ""), {}, depth + 1)
            ubos.extend(child.get("ubos", []))
            chain.extend(child.get("ownership_chain", []))
            if child.get("source") == "fallback":
                source = "fallback"

    return {"ubos": ubos, "ownership_chain": chain, "depth": depth, "source": source}
