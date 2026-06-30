"""
ARGUS Community Edition configuration.

Community Edition is a zero-cost, self-hostable path designed for NGOs,
microfinance institutions, and community banks that cannot afford
enterprise Azure subscriptions but still need defensible KYC tooling.

Key differences from the full Azure-backed edition:
  - Uses GPT-4o-mini by default (configurable to any OpenAI-compatible endpoint)
  - Replaces Azure Cosmos DB with SQLite
  - Replaces Azure AI Search with Qdrant (local vector DB)
  - Replaces Azure Document Intelligence with Tesseract OCR
  - Ships with a pre-seeded open regulatory corpus (FATF, Basel AML Index,
    Open Sanctions) — no licensed data required
  - Packaged as a single Docker Compose stack: one command to run
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class LLMTier(Enum):
    FULL = "gpt-4o"            # Enterprise: best reasoning, highest cost
    COMMUNITY = "gpt-4o-mini"  # Community: fast, low cost, still capable
    LOCAL = "ollama/llama3"    # Fully local: no API calls, for air-gapped use


class OCRBackend(Enum):
    AZURE = "azure_document_intelligence"
    TESSERACT = "tesseract"  # Community default — free, open source


class VectorBackend(Enum):
    AZURE_SEARCH = "azure_ai_search"
    QDRANT = "qdrant"  # Community default — free, self-hosted


class EntityStoreBackend(Enum):
    COSMOS = "azure_cosmos_db"
    SQLITE = "sqlite"  # Community default


@dataclass
class CommunityConfig:
    """
    Runtime configuration for Community Edition.
    Defaults are chosen to require zero cloud credentials.
    """
    llm_tier: LLMTier = LLMTier.COMMUNITY
    ocr_backend: OCRBackend = OCRBackend.TESSERACT
    vector_backend: VectorBackend = VectorBackend.QDRANT
    entity_store: EntityStoreBackend = EntityStoreBackend.SQLITE

    # OpenAI-compatible endpoint — swap in Azure, Ollama, etc.
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = field(default_factory=lambda: LLMTier.COMMUNITY.value)

    # Local paths (used when Azure services are disabled)
    sqlite_path: str = "data/community.db"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "argus_community_kb"

    # Open regulatory corpus (pre-seeded, no license required)
    use_open_corpus: bool = True
    open_corpus_path: str = "community/knowledge_base/"

    # NGO onboarding — relaxed defaults for known low-risk entity types
    ngo_jurisdiction_allowlist: list[str] = field(default_factory=lambda: [
        "DE", "NL", "SE", "NO", "DK", "FI", "CH", "AT", "FR", "GB",
        "CA", "AU", "NZ", "JP", "SG",
    ])

    @classmethod
    def for_ngo(cls) -> "CommunityConfig":
        """Preset for NGOs — open corpus, relaxed defaults, SQLite + Qdrant."""
        return cls(
            llm_tier=LLMTier.COMMUNITY,
            ocr_backend=OCRBackend.TESSERACT,
            vector_backend=VectorBackend.QDRANT,
            entity_store=EntityStoreBackend.SQLITE,
            use_open_corpus=True,
        )

    @classmethod
    def for_microfinance(cls) -> "CommunityConfig":
        """Preset for microfinance lenders — higher volume, batch-optimized."""
        return cls(
            llm_tier=LLMTier.COMMUNITY,
            ocr_backend=OCRBackend.TESSERACT,
            vector_backend=VectorBackend.QDRANT,
            entity_store=EntityStoreBackend.SQLITE,
            use_open_corpus=True,
        )

    @classmethod
    def air_gapped(cls) -> "CommunityConfig":
        """Fully local — no outbound API calls. Requires local Ollama instance."""
        return cls(
            llm_tier=LLMTier.LOCAL,
            llm_base_url="http://localhost:11434/v1",
            llm_model="ollama/llama3",
            ocr_backend=OCRBackend.TESSERACT,
            vector_backend=VectorBackend.QDRANT,
            entity_store=EntityStoreBackend.SQLITE,
            use_open_corpus=True,
        )
