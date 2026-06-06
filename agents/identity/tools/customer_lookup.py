"""customer_lookup — queries synthetic entity registry in Cosmos DB."""
from config import get_cosmos_database

async def customer_lookup(entity_name: str, entity_type: str, reg_number: str | None) -> dict:
    try:
        db = get_cosmos_database()
        container = db.get_container_client("entities")
        query = (
            "SELECT * FROM c WHERE "
            "LOWER(c.name) = LOWER(@name) AND c.entity_type = @type"
        )
        params = [
            {"name": "@name", "value": entity_name},
            {"name": "@type", "value": entity_type},
        ]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        if items:
            return {"found": True, "record": items[0]}
        return {"found": False, "record": None}
    except Exception as e:
        print(f"[customer_lookup] Cosmos DB unavailable: {e}. Using mock.")
        return {
            "found": True,
            "record": {
                "entity_id":   "MOCK-001",
                "name":        entity_name,
                "entity_type": entity_type,
                "address":     "123 Synthetic Street, Amsterdam, NL",
                "note":        "Mock record — Cosmos DB not provisioned yet",
            },
        }
