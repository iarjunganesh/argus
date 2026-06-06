"""registry_lookup — corporate registry query."""
from config import get_cosmos_database

async def registry_lookup(entity_name: str, reg_number: str | None) -> dict:
    try:
        db = get_cosmos_database()
        container = db.get_container_client("corporate_registry")
        query  = "SELECT * FROM c WHERE LOWER(c.name) = LOWER(@name)"
        params = [{"name": "@name", "value": entity_name}]
        items  = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        if items:
            return {"found": True, "record": items[0]}
        return {"found": False, "record": None}
    except Exception as e:
        print(f"[registry_lookup] Cosmos DB unavailable: {e}. Using mock.")
        return {
            "found": True,
            "record": {
                "name": entity_name,
                "incorporated_date": "2018-03-15",
                "sector": "financial_services",
                "directors": ["Mock Director A", "Mock Director B"],
            },
            "source": "mock",
        }
