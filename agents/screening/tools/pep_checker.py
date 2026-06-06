"""pep_checker — checks entity against synthetic PEP database in Cosmos DB."""
from config import get_cosmos_database

async def pep_checker(entity_name: str, dob: str, nationality: str) -> dict:
    try:
        db = get_cosmos_database()
        container = db.get_container_client("pep_database")
        query = "SELECT * FROM c WHERE LOWER(c.name) = LOWER(@name)"
        params = [{"name": "@name", "value": entity_name}]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        if items:
            pep = items[0]
            return {
                "hit": True,
                "findings": [{
                    "type":       "pep",
                    "match":      f"{pep.get('name')} — {pep.get('role', 'Unknown role')} ({pep.get('country', nationality)}, {pep.get('period', 'Unknown period')})",
                    "confidence": 0.92,
                    "source":     "synthetic_pep_db",
                }],
            }
        return {"hit": False, "findings": []}

    except Exception as e:
        print(f"[pep_checker] Cosmos DB unavailable: {e}. Using mock.")
        return {"hit": False, "findings": [], "source": "mock"}
