"""
create_knowledge_bases.py
Creates the three Foundry IQ knowledge bases for ARGUS.
Run once after Azure resources are provisioned.
Usage: python foundry_iq/create_knowledge_bases.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

KNOWLEDGE_BASES = [
    {
        "name":        os.getenv("FOUNDRY_IQ_KB_REGULATIONS", "argus-kb-regulations"),
        "description": "FATF 40 Recommendations, 4AMLD/6AMLD, GDPR Art.9, DORA regulatory text",
        "index_name":  "argus-regulations-index",
    },
    {
        "name":        os.getenv("FOUNDRY_IQ_KB_SANCTIONS", "argus-kb-sanctions"),
        "description": "Synthetic sanctions data (OFAC/UN/EU/UK schema)",
        "index_name":  "argus-sanctions-index",
    },
    {
        "name":        os.getenv("FOUNDRY_IQ_KB_ADVERSEMEDIA", "argus-kb-adversemedia"),
        "description": "Synthetic adverse media news corpus",
        "index_name":  "argus-media-index",
    },
]

def create_knowledge_bases():
    """
    Foundry IQ knowledge bases are backed by Azure AI Search indexes.
    This function delegates to create_search_indexes.py which sets up
    the indexes with the correct schema and semantic configuration.
    """
    print("Creating Foundry IQ knowledge bases (Azure AI Search indexes)...")
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from infra.create_search_indexes import create_search_indexes
        create_search_indexes()
        print("\nAll Foundry IQ knowledge bases ready. Run index scripts next:")
        print("  python foundry_iq/index_regulations.py")
        print("  python foundry_iq/index_sanctions_and_media.py")
    except KeyError as e:
        print(f"Missing environment variable: {e}. Run infra/setup.ps1 first.")

if __name__ == "__main__":
    create_knowledge_bases()
