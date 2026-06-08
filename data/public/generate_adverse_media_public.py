"""
Generate the public-source adverse-media corpus used by ARGUS demos.

The output is intentionally small and curated so the demo can show a public
data-backed screening path without depending on live web ingestion.

Usage: python data/public/generate_adverse_media_public.py
"""
import json
from pathlib import Path


OUTPUT_FILE = Path(__file__).parent / "adverse_media_public.jsonl"

PUBLIC_ARTICLES = [
    {
        "article_id": "PUB-AM-001",
        "headline": "Wirecard AG public coverage highlights accounting irregularities and insolvency proceedings.",
        "body": "Public reporting on Wirecard describes accounting irregularities, investor losses, and insolvency proceedings that raised major governance and control concerns.",
        "source": "public_enforcement_summary",
        "source_kind": "public",
        "source_reference": "public_reporting_and_enforcement_summaries",
        "published_at": "2020-06-25",
        "sentiment": "negative",
        "tags": ["fraud", "accounting", "governance"],
    },
    {
        "article_id": "PUB-AM-002",
        "headline": "Danske Bank A/S public coverage references historical AML control weaknesses in Estonia.",
        "body": "Public coverage of Danske Bank's Estonia branch discusses historical anti-money-laundering control weaknesses, supervisory scrutiny, and remediation efforts.",
        "source": "public_enforcement_summary",
        "source_kind": "public",
        "source_reference": "public_reporting_and_enforcement_summaries",
        "published_at": "2018-09-19",
        "sentiment": "negative",
        "tags": ["aml", "controls", "governance"],
    },
    {
        "article_id": "PUB-AM-003",
        "headline": "Westpac Banking Corporation public coverage references AML and sanctions screening failings.",
        "body": "Public reporting on Westpac describes compliance control failures, including weaknesses in transaction monitoring and sanctions screening processes.",
        "source": "public_enforcement_summary",
        "source_kind": "public",
        "source_reference": "public_reporting_and_enforcement_summaries",
        "published_at": "2020-11-24",
        "sentiment": "negative",
        "tags": ["aml", "sanctions", "monitoring"],
    },
    {
        "article_id": "PUB-AM-004",
        "headline": "Binance public coverage references compliance remediation following regulatory settlement.",
        "body": "Public coverage of Binance references compliance remediation, control enhancements, and ongoing supervisory scrutiny after major settlement activity.",
        "source": "public_enforcement_summary",
        "source_kind": "public",
        "source_reference": "public_reporting_and_enforcement_summaries",
        "published_at": "2023-11-21",
        "sentiment": "negative",
        "tags": ["compliance", "controls", "settlement"],
    },
]


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as handle:
        for article in PUBLIC_ARTICLES:
            handle.write(json.dumps(article, ensure_ascii=False) + "\n")
    print(f"Generated {len(PUBLIC_ARTICLES)} public adverse-media articles -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()