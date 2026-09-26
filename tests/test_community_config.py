"""Community Edition presets need no cloud credentials."""

from community import CommunityConfig, LLMTier
from community.config import EntityStoreBackend, OCRBackend, VectorBackend


def test_defaults_are_local_and_free():
    cfg = CommunityConfig()

    assert cfg.llm_tier is LLMTier.COMMUNITY
    assert cfg.llm_model == "gpt-4o-mini"
    assert cfg.ocr_backend is OCRBackend.TESSERACT
    assert cfg.vector_backend is VectorBackend.QDRANT
    assert cfg.entity_store is EntityStoreBackend.SQLITE
    assert "SE" in cfg.ngo_jurisdiction_allowlist


def test_allowlist_is_not_shared_between_instances():
    first, second = CommunityConfig(), CommunityConfig()
    first.ngo_jurisdiction_allowlist.append("XX")

    assert "XX" not in second.ngo_jurisdiction_allowlist


def test_ngo_and_microfinance_presets_use_the_open_corpus():
    for cfg in (CommunityConfig.for_ngo(), CommunityConfig.for_microfinance()):
        assert cfg.use_open_corpus is True
        assert cfg.entity_store is EntityStoreBackend.SQLITE


def test_air_gapped_preset_calls_only_localhost():
    cfg = CommunityConfig.air_gapped()

    assert cfg.llm_tier is LLMTier.LOCAL
    assert cfg.llm_base_url.startswith("http://localhost:")
    assert cfg.qdrant_url.startswith("http://localhost:")
