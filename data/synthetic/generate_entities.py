"""
Generate synthetic entity profiles for ARGUS.
Produces 10,000 individual and corporate entities — zero real PII.
Output: data/synthetic/entities.jsonl
"""
import json
import random
from faker import Faker
from pathlib import Path

fake = Faker()
Faker.seed(42)
random.seed(42)

OUTPUT_FILE = Path(__file__).parent / "entities.jsonl"

JURISDICTIONS = ["NL", "DE", "GB", "SE", "NO", "DK", "FI", "CH", "LU", "CY", "PA", "KY", "BVI"]
ENTITY_TYPES  = ["individual", "corporate"]
SECTORS       = ["financial_services", "real_estate", "technology", "trading", "consulting", "manufacturing"]

HIGH_RISK_JURISDICTIONS = {"PA", "KY", "BVI", "CY"}   # for synthetic risk flags

def generate_individual() -> dict:
    nationality = random.choice(JURISDICTIONS)
    return {
        "entity_id":     f"IND-{fake.uuid4()[:8].upper()}",
        "entity_type":   "individual",
        "name":          fake.name(),
        "aliases":       [fake.last_name() + " " + fake.first_name()],
        "nationality":   nationality,
        "date_of_birth": fake.date_of_birth(minimum_age=25, maximum_age=75).isoformat(),
        "address":       fake.address().replace("\n", ", "),
        "tax_id":        fake.numerify("##########"),
        "is_pep":        random.random() < 0.05,     # 5% PEP rate
        "risk_flag":     nationality in HIGH_RISK_JURISDICTIONS,
    }

def generate_corporate() -> dict:
    jurisdiction = random.choice(JURISDICTIONS)
    return {
        "entity_id":           f"CRP-{fake.uuid4()[:8].upper()}",
        "entity_type":         "corporate",
        "name":                fake.company(),
        "aliases":             [fake.company_suffix() + " " + fake.last_name() + " Ltd"],
        "jurisdiction":        jurisdiction,
        "registration_number": fake.bothify("??-####-??-#####").upper(),
        "incorporated_date":   fake.date_between(start_date="-20y", end_date="-1y").isoformat(),
        "sector":              random.choice(SECTORS),
        "registered_address":  fake.address().replace("\n", ", "),
        "directors":           [fake.name() for _ in range(random.randint(1, 4))],
        "risk_flag":           jurisdiction in HIGH_RISK_JURISDICTIONS,
    }

def main():
    print("Generating synthetic entity profiles...")
    with open(OUTPUT_FILE, "w") as f:
        for i in range(7000):   # 70% individuals
            entity = generate_individual()
            f.write(json.dumps(entity) + "\n")
        for i in range(3000):   # 30% corporates
            entity = generate_corporate()
            f.write(json.dumps(entity) + "\n")

    print(f"Generated 10,000 entities → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
