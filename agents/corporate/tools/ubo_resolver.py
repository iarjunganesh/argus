"""
ubo_resolver — Recursive UBO graph traversal.
Traverses synthetic corporate ownership graph in Cosmos DB.
Stops at individuals with >25% ownership or at depth limit (5 levels).
"""
from config import get_cosmos_database

OWNERSHIP_THRESHOLD = 25.0   # FATF standard UBO threshold
MAX_DEPTH = 5

async def ubo_resolver(entity_name: str, registry_result: dict, depth: int = 0) -> dict:
    if depth >= MAX_DEPTH:
        return {"ubos": [], "ownership_chain": [], "depth": depth, "note": "Max depth reached"}

    try:
        db = get_cosmos_database()
        container = db.get_container_client("corporate_graph")

        query  = "SELECT * FROM c WHERE LOWER(c.parent_entity) = LOWER(@name)"
        params = [{"name": "@name", "value": entity_name}]
        nodes  = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        ubos = []
        chain = []

        for node in nodes:
            ownership_pct = node.get("ownership_percentage", 0)
            node_type     = node.get("entity_type", "corporate")
            node_info     = {
                "name":               node.get("name"),
                "entity_type":        node_type,
                "ownership_pct":      ownership_pct,
                "jurisdiction":       node.get("jurisdiction", ""),
                "depth":              depth + 1,
            }
            chain.append(node_info)

            if node_type == "individual" and ownership_pct >= OWNERSHIP_THRESHOLD:
                # Found a UBO
                ubos.append({**node_info, "is_ubo": True})
            elif node_type == "corporate":
                # Recurse into corporate node
                child = await ubo_resolver(node.get("name", ""), {}, depth + 1)
                ubos.extend(child.get("ubos", []))
                chain.extend(child.get("ownership_chain", []))

        return {"ubos": ubos, "ownership_chain": chain, "depth": depth}

    except Exception as e:
        print(f"[ubo_resolver] Cosmos DB unavailable: {e}. Using mock.")
        return {
            "ubos": [{"name": "Mock UBO Person", "ownership_pct": 51.0, "jurisdiction": "NL", "is_ubo": True}],
            "ownership_chain": [],
            "depth": 1,
            "source": "mock",
        }
