"""
generate_transactions.py
Generates synthetic transaction ledger with embedded AML patterns.
Patterns: structuring (below threshold), layering, normal baseline.
Output: data/synthetic/transactions.jsonl
"""
import json, random
from faker import Faker
from pathlib import Path
from datetime import datetime, timedelta

fake = Faker(); Faker.seed(33); random.seed(33)
OUTPUT = Path(__file__).parent / "transactions.jsonl"

CURRENCIES   = ["EUR", "USD", "GBP", "SEK", "NOK"]
THRESHOLD    = 10_000   # reporting threshold

def random_date(days_back=365) -> str:
    d = datetime.now() - timedelta(days=random.randint(0, days_back))
    return d.strftime("%Y-%m-%d")

def normal_tx(entity_name: str) -> dict:
    return {
        "tx_id":        f"TX-{fake.uuid4()[:8].upper()}",
        "entity_name":  entity_name,
        "amount":       round(random.uniform(500, 100_000), 2),
        "currency":     random.choice(CURRENCIES),
        "date":         random_date(),
        "counterparty": fake.company(),
        "pattern":      "normal",
    }

def structuring_tx(entity_name: str, idx: int) -> dict:
    """Transaction just below reporting threshold."""
    return {
        "tx_id":        f"TX-STR-{fake.uuid4()[:6].upper()}-{idx}",
        "entity_name":  entity_name,
        "amount":       round(random.uniform(8_500, 9_900), 2),
        "currency":     "EUR",
        "date":         random_date(days_back=30),
        "counterparty": fake.company(),
        "pattern":      "structuring",
        "note":         "Below €10K threshold",
    }

def main():
    print("Generating synthetic transaction ledger...")
    # Load entity names
    entity_file = Path(__file__).parent / "entities.jsonl"
    if not entity_file.exists():
        print("Run generate_entities.py first.")
        return

    entities = [json.loads(l)["name"] for l in entity_file.read_text().splitlines()[:200] if l.strip()]

    total = 0
    with open(OUTPUT, "w") as f:
        for entity in entities:
            n_normal  = random.randint(10, 50)
            inject_aml= random.random() < 0.10    # 10% of entities have AML patterns

            for _ in range(n_normal):
                f.write(json.dumps(normal_tx(entity)) + "\n")
                total += 1

            if inject_aml:
                for i in range(random.randint(5, 9)):
                    f.write(json.dumps(structuring_tx(entity, i)) + "\n")
                    total += 1

    print(f"Generated {total} transactions for {len(entities)} entities → {OUTPUT}")

if __name__ == "__main__":
    main()
