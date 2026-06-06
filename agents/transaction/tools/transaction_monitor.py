"""transaction_monitor — loads synthetic transaction history from Cosmos DB."""
from config import get_cosmos_database

async def transaction_monitor(entity_name: str) -> dict:
    try:
        db = get_cosmos_database()
        container = db.get_container_client("transactions")
        query  = "SELECT * FROM c WHERE LOWER(c.entity_name) = LOWER(@name) ORDER BY c.date DESC OFFSET 0 LIMIT 500"
        params = [{"name": "@name", "value": entity_name}]
        items  = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        if not items:
            return {"count": 0, "transactions": [], "date_range": {}}

        dates = [t.get("date", "") for t in items if t.get("date")]
        return {
            "count":        len(items),
            "transactions": items,
            "date_range":   {"from": min(dates), "to": max(dates)} if dates else {},
        }
    except Exception as e:
        print(f"[transaction_monitor] Cosmos DB unavailable: {e}. Using mock.")
        return _mock_transaction_history()


def _mock_transaction_history() -> dict:
    import random
    from faker import Faker
    fake = Faker(); fake.seed_instance(42)
    txs = []
    # Inject structuring pattern: 7 transactions just below €10,000
    for i in range(7):
        txs.append({"id": f"TX-STR-{i}", "amount": round(9500 + random.uniform(-300, 300), 2),
                    "currency": "EUR", "date": f"2026-04-{10+i:02d}",
                    "counterparty": fake.company(), "note": "synthetic_structuring_pattern"})
    # Normal transactions
    for i in range(43):
        txs.append({"id": f"TX-NRM-{i}", "amount": round(random.uniform(500, 50000), 2),
                    "currency": "EUR", "date": fake.date_between(start_date="-12m", end_date="today").isoformat(),
                    "counterparty": fake.company()})
    return {"count": len(txs), "transactions": txs, "date_range": {"from": "2025-06-01", "to": "2026-05-31"}, "source": "mock"}
