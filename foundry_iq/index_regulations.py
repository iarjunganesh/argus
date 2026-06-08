"""
index_regulations.py
Indexes public regulatory text (FATF/4AMLD/6AMLD) into Foundry IQ KB-Regulations.
Source files should be placed in data/public/ before running.
"""
import os, json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.env_loader import load_repo_env

load_repo_env(__file__)

DATA_DIR = Path(__file__).parent.parent / "data" / "public"
KB_NAME  = os.getenv("FOUNDRY_IQ_KB_REGULATIONS", "argus-kb-regulations")

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


def index_regulations():
    print(f"Indexing regulatory text into Foundry IQ {KB_NAME}...")

    # If no files in data/public, use embedded regulation documents above
    txt_files = list(DATA_DIR.glob("*.txt")) + list(DATA_DIR.glob("*.pdf"))
    if txt_files:
        print(f"  Found {len(txt_files)} documents in {DATA_DIR} — loading from files.")
    else:
        print(f"  No files in {DATA_DIR} — using embedded FATF/4AMLD/6AMLD/GDPR/DORA text.")

    docs_to_index = list(REGULATION_DOCUMENTS)  # start with embedded docs

    # Optionally load from txt files too
    for txt_file in txt_files:
        content = txt_file.read_text(encoding="utf-8", errors="ignore")
        docs_to_index.append({
            "id": txt_file.stem,
            "title": txt_file.stem.replace("-", " ").replace("_", " ").title(),
            "source_doc": txt_file.name,
            "category": "regulation",
            "content": content[:5000],
            "entity_name": "",
            "metadata_json": json.dumps({"file": txt_file.name}),
        })

    # Ensure all docs have required fields
    for doc in docs_to_index:
        doc.setdefault("entity_name", "")
        doc.setdefault("metadata_json", "{}")

    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key      = os.environ["AZURE_SEARCH_API_KEY"]
        client   = SearchClient(endpoint, KB_NAME, AzureKeyCredential(key))

        result = client.upload_documents(docs_to_index)
        succeeded = sum(1 for r in result if r.succeeded)
        print(f"  ✅ {succeeded}/{len(docs_to_index)} regulation documents indexed into {KB_NAME}")

    except ImportError:
        import urllib.request

        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/")
        key      = os.environ["AZURE_SEARCH_API_KEY"]
        batch_size = 100
        total_ok = 0
        for i in range(0, len(docs_to_index), batch_size):
            batch = docs_to_index[i:i + batch_size]
            payload = {
                "value": [{"@search.action": "mergeOrUpload", **doc} for doc in batch]
            }
            request = urllib.request.Request(
                f"{endpoint}/indexes/{KB_NAME}/docs/index?api-version=2023-11-01",
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json", "api-key": key},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                response.read()
            total_ok += len(batch)

        print(f"  ✅ {total_ok}/{len(docs_to_index)} regulation documents indexed into {KB_NAME} via REST")

    except Exception as e:
        print(f"  ❌ Error indexing regulations: {e}")
        raise

if __name__ == "__main__":
    index_regulations()
