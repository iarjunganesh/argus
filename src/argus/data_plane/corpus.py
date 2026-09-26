"""The documents behind each knowledge base, in the shape the search indexes store.

One builder per knowledge base. The local retriever searches these documents in memory, and the
`infra/foundry_iq/` scripts upload the same documents to Azure AI Search, so both backends answer
from identical content.
"""

from __future__ import annotations

import json
from pathlib import Path

# Summaries of public regulatory texts. Each entry names its source document; the wording is a
# summary for retrieval, not the legal text.
REGULATION_DOCUMENTS = [
    {
        "id": "fatf-rec-10",
        "title": "FATF Recommendation 10 — Customer Due Diligence",
        "source_doc": "fatf-40-recommendations.pdf",
        "category": "regulation",
        "content": (
            "FATF Recommendation 10 requires financial institutions to undertake "
            "customer due diligence (CDD) measures when: establishing business relations; "
            "carrying out occasional transactions above USD/EUR 15,000; there is a "
            "suspicion of money laundering or terrorist financing; the institution has "
            "doubts about the veracity of previously obtained identification data. "
            "CDD measures include: identifying the customer and verifying identity using "
            "reliable, independent source documents; identifying the beneficial owner and "
            "taking reasonable measures to verify identity; understanding the nature and "
            "purpose of the business relationship; conducting ongoing due diligence."
        ),
    },
    {
        "id": "fatf-rec-12",
        "title": "FATF Recommendation 12 — Politically Exposed Persons",
        "source_doc": "fatf-40-recommendations.pdf",
        "category": "regulation",
        "content": (
            "FATF Recommendation 12: In addition to normal CDD measures, financial "
            "institutions must apply enhanced due diligence to politically exposed "
            "persons (PEPs). For foreign PEPs, institutions must: have risk management "
            "systems to determine if the customer is a PEP; obtain senior management "
            "approval to establish or continue business; take reasonable measures to "
            "establish the source of wealth and funds; conduct enhanced ongoing monitoring "
            "of the relationship. Domestic PEPs and those in international organisations "
            "should be subject to risk-based enhanced measures."
        ),
    },
    {
        "id": "fatf-rec-20",
        "title": "FATF Recommendation 20 — Reporting of Suspicious Transactions",
        "source_doc": "fatf-40-recommendations.pdf",
        "category": "regulation",
        "content": (
            "FATF Recommendation 20: If a financial institution suspects or has "
            "reasonable grounds to suspect that funds are the proceeds of a criminal "
            "activity, or are related to terrorist financing, it should be required by "
            "law to report promptly to the financial intelligence unit (FIU). Countries "
            "should ensure that financial institutions report all suspicious transactions "
            "regardless of whether they are thought to involve tax matters. Countries "
            "should consider adopting measures to allow financial institutions to carry "
            "out the transaction before filing a STR, where not reporting would tip off "
            "the customer."
        ),
    },
    {
        "id": "4amld-art-18",
        "title": "4AMLD Article 18 — Enhanced Due Diligence",
        "source_doc": "4amld-directive.pdf",
        "category": "regulation",
        "content": (
            "4AMLD Article 18 requires Member States to ensure that obliged entities "
            "apply enhanced customer due diligence measures in situations which by their "
            "nature can present a higher risk of money laundering or terrorist financing. "
            "High-risk third countries identified by the Commission must be subject to "
            "enhanced due diligence. Enhanced measures include: obtaining additional "
            "information on the customer and beneficial owner; obtaining additional "
            "information on the intended nature of the business relationship; obtaining "
            "information on the source of funds; obtaining senior management approval; "
            "conducting enhanced monitoring of the business relationship."
        ),
    },
    {
        "id": "6amld-art-3",
        "title": "6AMLD Article 3 — Predicate Offences",
        "source_doc": "6amld-directive.pdf",
        "category": "regulation",
        "content": (
            "6AMLD extends the list of predicate offences for money laundering to "
            "include 22 categories: participation in an organised criminal group; "
            "terrorism including financing; trafficking in human beings; sexual "
            "exploitation; illicit trafficking in narcotic drugs; illicit trafficking in "
            "weapons; illicit trafficking in stolen goods; corruption and bribery; fraud; "
            "counterfeiting currency; counterfeiting products; environmental crime; "
            "murder and grievous bodily injury; kidnapping, illegal restraint and "
            "hostage-taking; robbery or theft; smuggling; extortion; forgery; piracy; "
            "insider trading and market manipulation; cybercrime; tax crimes."
        ),
    },
    {
        "id": "gdpr-art-9",
        "title": "GDPR Article 9 — Processing of Special Category Data",
        "source_doc": "gdpr-regulation.pdf",
        "category": "regulation",
        "content": (
            "GDPR Article 9 prohibits processing of personal data revealing racial or "
            "ethnic origin, political opinions, religious or philosophical beliefs, trade "
            "union membership, genetic data, biometric data for uniquely identifying a "
            "natural person, data concerning health, sex life or sexual orientation. "
            "Exceptions apply where: the data subject has given explicit consent; "
            "processing is necessary for carrying out obligations in employment law; "
            "processing is necessary for vital interests; the Foundation, association or "
            "not-for-profit body processes data as part of its legitimate activities; "
            "processing relates to data manifestly made public; processing is necessary "
            "for legal claims; processing is necessary for reasons of substantial public "
            "interest under Union or Member State law."
        ),
    },
    {
        "id": "dora-art-5",
        "title": "DORA Article 5 — ICT Risk Management Framework",
        "source_doc": "dora-regulation.pdf",
        "category": "regulation",
        "content": (
            "DORA Article 5 requires financial entities to have in place an internal "
            "governance and control framework that ensures an effective and prudent "
            "management of ICT risk. The management body shall define, approve, oversee "
            "and be accountable for the implementation of all arrangements related to the "
            "ICT risk management framework. ICT risk management framework shall include "
            "strategies, policies, procedures, ICT protocols and tools necessary to "
            "protect all information assets and ICT assets including computer software, "
            "hardware, servers, and all relevant physical components."
        ),
    },
    {
        "id": "wolfsberg-kyc",
        "title": "Wolfsberg Group — KYC Principles",
        "source_doc": "wolfsberg-kyc-principles.pdf",
        "category": "regulation",
        "content": (
            "The Wolfsberg Group KYC Principles state that banks will endeavour to "
            "accept only those customers whose source of wealth and funds can be "
            "reasonably established to be legitimate. The primary responsibility for this "
            "lies with the relationship manager who sponsors acceptance of the customer. "
            "Basic account opening requires: identification of customer identity; "
            "identification of beneficial ownership for legal entity customers; "
            "purpose and nature of the account; source of wealth for high-risk customers; "
            "references or other evidence of customer reputation where appropriate."
        ),
    },
]


def load_jsonl(path: Path) -> list[dict]:
    """Records from a JSON Lines file, or none if the file does not exist."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def regulation_documents() -> list[dict]:
    return [{**doc, "entity_name": "", "metadata_json": "{}"} for doc in REGULATION_DOCUMENTS]


def sanctions_documents(records: list[dict]) -> list[dict]:
    docs = []
    for r in records:
        aliases = r.get("aliases", [])
        name = r.get("name", "")
        content = (
            f"{name}. Aliases: {', '.join(aliases)}. "
            f"List: {r.get('list_type', '')}. Program: {r.get('program', '')}. "
            f"Reason: {r.get('reason', '')}. "
            f"Nationality/Country: {r.get('nationality') or r.get('country', '')}."
        )
        docs.append(
            {
                "id": r["sanctions_id"],
                "title": f"{name} — {r.get('list_type', 'SANCTIONS')}",
                "content": content,
                "entity_name": " | ".join([name, *aliases]),
                "source_doc": r.get("list_type", "SYNTHETIC_SANCTIONS"),
                "category": "sanctions",
                "metadata_json": json.dumps(
                    {
                        "program": r.get("program"),
                        "is_active": r.get("is_active"),
                        "entity_type": r.get("entity_type"),
                    }
                ),
            }
        )
    return docs


def adverse_media_documents(synthetic: list[dict], public: list[dict]) -> list[dict]:
    """Negative coverage only: synthetic articles plus public enforcement summaries."""
    negative = [(r, "synthetic") for r in synthetic if r.get("sentiment") == "negative"]
    negative += [(r, "public") for r in public if r.get("sentiment", "negative") == "negative"]
    return [
        {
            "id": r.get("article_id") or r.get("document_id") or r.get("id"),
            "title": r.get("headline", "")[:200],
            "content": r.get("body", r.get("headline", ""))[:2000],
            "entity_name": "",
            "source_doc": r.get("source", "SYNTHETIC_NEWS"),
            "category": "adverse_media",
            "metadata_json": json.dumps(
                {
                    "source_kind": r.get("source_kind", kind),
                    "published_at": r.get("published_at"),
                    "sentiment": r.get("sentiment"),
                    "tags": r.get("tags", []),
                    "source_reference": r.get("source_reference"),
                }
            ),
        }
        for r, kind in negative
    ]
