"""
Generate synthetic adverse media news articles.
Uses templates — no real entities, no GPT-4o API calls needed.
Output: data/synthetic/adverse_media.jsonl
"""
import json
import random
from faker import Faker
from pathlib import Path

fake = Faker()
Faker.seed(77)
random.seed(77)

OUTPUT_FILE = Path(__file__).parent / "adverse_media.jsonl"

NEGATIVE_TEMPLATES = [
    "{company} under investigation for alleged {crime} by {regulator}.",
    "{person} faces charges related to {crime} in {country}.",
    "Regulators probe {company} over suspected {crime} activities.",
    "{company} director {person} linked to {crime} network, sources say.",
    "{country} authorities freeze assets of {company} amid {crime} probe.",
    "{person} named in {country} court proceedings over {crime} allegations.",
    "Anti-money laundering watchdog flags {company} for suspicious transactions.",
    "{company} fined by {regulator} for compliance failures in {year}.",
]

POSITIVE_TEMPLATES = [
    "{company} reports record revenue for {year} fiscal year.",
    "{company} expands operations in {country} with new partnership.",
    "{person} appointed as CEO of {company} effective {year}.",
    "{company} wins {country} government contract worth millions.",
    "Industry awards recognise {company} for compliance excellence.",
]

CRIMES      = ["money laundering", "fraud", "bribery", "tax evasion", "sanctions evasion", "procurement irregularities"]
REGULATORS  = ["Financial Intelligence Unit", "Central Bank", "SEC equivalent", "Anti-Corruption Bureau", "Tax Authority"]

def generate_article(negative: bool = True) -> dict:
    templates  = NEGATIVE_TEMPLATES if negative else POSITIVE_TEMPLATES
    template   = random.choice(templates)
    article_text = template.format(
        company   = fake.company(),
        person    = fake.name(),
        crime     = random.choice(CRIMES),
        regulator = random.choice(REGULATORS),
        country   = fake.country(),
        year      = random.randint(2018, 2025),
    )
    return {
        "article_id":   f"NEWS-{fake.uuid4()[:8].upper()}",
        "headline":     article_text,
        "body":         article_text + " " + fake.paragraph(nb_sentences=5),
        "source":       f"Synthetic {fake.company()} News",
        "published_at": fake.date_between(start_date="-5y", end_date="today").isoformat(),
        "sentiment":    "negative" if negative else "neutral",
        "tags":         [random.choice(CRIMES)] if negative else ["business"],
    }

def main():
    print("Generating synthetic adverse media corpus...")
    with open(OUTPUT_FILE, "w") as f:
        # 400 negative articles (main screening signal)
        for _ in range(400):
            f.write(json.dumps(generate_article(negative=True)) + "\n")
        # 600 neutral/positive (noise — makes screening non-trivial)
        for _ in range(600):
            f.write(json.dumps(generate_article(negative=False)) + "\n")
    print(f"Generated 1,000 articles → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
