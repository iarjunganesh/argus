"""
Generate synthetic sanctions dataset (OFAC/UN/EU/UK schema).
Zero real names — all Faker-generated. 500 entries.
Output: data/synthetic/sanctions.jsonl
"""
import json
import random
from faker import Faker
from pathlib import Path
from datetime import date

fake = Faker()
Faker.seed(99)
random.seed(99)

OUTPUT_FILE = Path(__file__).parent / "sanctions.jsonl"

LIST_TYPES    = ["OFAC_SDN", "UN_CONSOLIDATED", "EU_CONSOLIDATED", "UK_HM_TREASURY"]
PROGRAMS      = ["NARCOTICS", "TERRORISM", "UKRAINE", "IRAN", "NORTH_KOREA", "SYRIA", "CYBER"]
ENTITY_TYPES  = ["individual", "entity", "vessel", "aircraft"]

def generate_sanctions_entry() -> dict:
    entity_type = random.choice(ENTITY_TYPES)
    entry = {
        "sanctions_id":   f"SYN-{fake.uuid4()[:10].upper()}",
        "list_type":      random.choice(LIST_TYPES),
        "program":        random.choice(PROGRAMS),
        "entity_type":    entity_type,
        "listed_date":    fake.date_between(start_date="-10y", end_date="today").isoformat(),
        "is_active":      random.random() < 0.85,
    }
    if entity_type == "individual":
        entry.update({
            "name":          fake.name(),
            "aliases":       [fake.name() for _ in range(random.randint(0, 3))],
            "nationality":   fake.country_code(),
            "date_of_birth": fake.date_of_birth(minimum_age=30, maximum_age=80).isoformat(),
            "reason":        f"Designated for {random.choice(PROGRAMS).lower()} activities.",
        })
    else:
        entry.update({
            "name":    fake.company(),
            "aliases": [fake.company() for _ in range(random.randint(0, 2))],
            "country": fake.country_code(),
            "reason":  f"Entity associated with {random.choice(PROGRAMS).lower()} network.",
        })
    return entry

def main():
    print("Generating synthetic sanctions dataset...")
    with open(OUTPUT_FILE, "w") as f:
        for _ in range(500):
            f.write(json.dumps(generate_sanctions_entry()) + "\n")
    print(f"Generated 500 sanctions entries → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
