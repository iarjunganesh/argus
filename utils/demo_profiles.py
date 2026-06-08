"""Deterministic demo scenarios so the documented UI examples map to stable risk outcomes."""


def _norm(value: str) -> str:
    return " ".join(
        value.strip().lower().replace(".", " ").replace(",", " ").replace("/", " ").split()
    )


# Common shorthand names used during demos map to canonical profiles.
NAME_ALIASES = {
    "wirecard": ("wirecard ag", "corporate", "DE"),
    "wirecard ag": ("wirecard ag", "corporate", "DE"),
    "cayman": ("cayman synth capital", "corporate", "KY"),
    "cayman synth": ("cayman synth capital", "corporate", "KY"),
    "cayman holdings": ("cayman synth capital", "corporate", "KY"),
    "cayman synth capital": ("cayman synth capital", "corporate", "KY"),
    "synthetic holdings": ("synthetic holdings b.v.", "corporate", "NL"),
    "synthetic holdings b v": ("synthetic holdings b.v.", "corporate", "NL"),
    "synthetic holdings b.v.": ("synthetic holdings b.v.", "corporate", "NL"),
    "jane": ("jane synthetic", "individual", "DE"),
    "jane doe": ("jane synthetic", "individual", "DE"),
    "jane synthetic": ("jane synthetic", "individual", "DE"),
}


def get_demo_profile(entity_name: str, entity_type: str, jurisdiction: str) -> dict | None:
    key = (entity_name.strip().lower(), entity_type.strip().lower(), jurisdiction.strip().upper())
    profile = DEMO_PROFILES.get(key)
    if profile is not None:
        return profile

    alias = NAME_ALIASES.get(_norm(entity_name))
    if alias is not None:
        return DEMO_PROFILES.get(alias)

    return None


DEMO_PROFILES = {
    ("jane synthetic", "individual", "DE"): {
        "identity": {
            "registry_match": True,
            "ocr_documents": 0,
            "discrepancies": [],
            "identity_score": 96,
            "verified_fields": ["name"],
        },
        "screening": {
            "sanctions_hit": False,
            "adverse_media_hit": False,
            "pep_hit": False,
            "findings": [],
            "screening_risk_score": 5,
            "foundry_iq_queries": 2,
        },
        "transaction": {
            "transaction_count": 8,
            "date_range": {"from": "2026-01-12", "to": "2026-05-28"},
            "structuring_flag": False,
            "layering_flag": False,
            "anomalous_transactions": [],
            "typology_hits": [],
            "transaction_risk_score": 5,
        },
    },
    ("synthetic holdings b.v.", "corporate", "NL"): {
        "identity": {
            "registry_match": True,
            "ocr_documents": 0,
            "discrepancies": [
                {"field": "address", "registry": "Amsterdam", "document": "Rotterdam", "severity": "medium"}
            ],
            "identity_score": 75,
            "verified_fields": ["name"],
        },
        "screening": {
            "sanctions_hit": False,
            "adverse_media_hit": True,
            "pep_hit": True,
            "findings": [
                {
                    "type": "pep",
                    "match": "Director identified as a domestic PEP with elevated scrutiny requirements",
                    "confidence": 0.88,
                    "source": "synthetic_pep_db",
                },
                {
                    "type": "adverse_media",
                    "match": "Negative press references governance concerns and beneficial ownership opacity",
                    "confidence": 0.79,
                    "foundry_iq_citation": {
                        "knowledge_base": "argus-kb-adversemedia",
                        "document": "synthetic_holdings_governance_watch.json",
                        "snippet_id": "demo-medium-001",
                        "published_at": "2026-04-18",
                        "tags": ["governance", "ownership"],
                    },
                },
            ],
            "screening_risk_score": 40,
            "foundry_iq_queries": 2,
        },
        "corporate": {
            "registry": {"found": True, "record": {"name": "Synthetic Holdings B.V.", "jurisdiction": "NL"}},
            "ubo_chain": {
                "ownership_chain": [
                    {"name": "Synthetic Holdings B.V.", "jurisdiction": "NL"},
                    {"name": "Canal Trustees Ltd.", "jurisdiction": "CY"},
                ],
                "depth": 2,
            },
            "jurisdiction_info": {"fatf_risk_tier": "standard"},
            "risk_flags": ["Layered ownership chain requires enhanced review of beneficial ownership documentation"],
            "corporate_score": 55,
        },
        "transaction": {
            "transaction_count": 26,
            "date_range": {"from": "2026-02-04", "to": "2026-06-03"},
            "structuring_flag": False,
            "layering_flag": True,
            "anomalous_transactions": [
                {"id": "TX-MED-01", "amount": 22000, "note": "rapid multi-hop transfer pattern"},
            ],
            "typology_hits": ["Rapid movement through intermediary accounts"],
            "transaction_risk_score": 20,
        },
    },
    ("cayman synth capital", "corporate", "KY"): {
        "identity": {
            "registry_match": True,
            "ocr_documents": 0,
            "discrepancies": [
                {"field": "incorporation_status", "registry": "active", "document": "pending verification", "severity": "high"}
            ],
            "identity_score": 55,
            "verified_fields": ["name"],
        },
        "screening": {
            "sanctions_hit": True,
            "adverse_media_hit": True,
            "pep_hit": True,
            "findings": [
                {
                    "type": "sanctions",
                    "match": "Strong sanctions-adjacent match tied to narcotics proceeds facilitation watchlist entry",
                    "confidence": 0.93,
                    "foundry_iq_citation": {
                        "knowledge_base": "argus-kb-sanctions",
                        "document": "synthetic_sanctions_watchlist.json",
                        "snippet_id": "demo-high-001",
                        "program": "Narcotics Trafficking",
                        "is_active": True,
                    },
                },
                {
                    "type": "pep",
                    "match": "Beneficial owner linked to a former minister requiring enhanced due diligence",
                    "confidence": 0.91,
                    "source": "synthetic_pep_db",
                },
                {
                    "type": "adverse_media",
                    "match": "Adverse media links the entity to procurement bribery and opaque offshore fund flows",
                    "confidence": 0.89,
                    "foundry_iq_citation": {
                        "knowledge_base": "argus-kb-adversemedia",
                        "document": "cayman_synth_capital_investigation.json",
                        "snippet_id": "demo-high-002",
                        "published_at": "2026-05-07",
                        "tags": ["bribery", "offshore", "aml"],
                    },
                },
            ],
            "screening_risk_score": 85,
            "foundry_iq_queries": 2,
        },
        "corporate": {
            "registry": {"found": True, "record": {"name": "Cayman Synth Capital", "jurisdiction": "KY"}},
            "ubo_chain": {
                "ownership_chain": [
                    {"name": "Cayman Synth Capital", "jurisdiction": "KY"},
                    {"name": "Blue Reef Nominees", "jurisdiction": "PA"},
                    {"name": "Harbor Frontier SPC", "jurisdiction": "KY"},
                ],
                "depth": 4,
            },
            "jurisdiction_info": {"fatf_risk_tier": "high"},
            "risk_flags": [
                "High-risk jurisdiction node: Blue Reef Nominees (PA)",
                "High-risk jurisdiction node: Harbor Frontier SPC (KY)",
            ],
            "corporate_score": 40,
        },
        "transaction": {
            "transaction_count": 54,
            "date_range": {"from": "2025-12-10", "to": "2026-06-04"},
            "structuring_flag": True,
            "layering_flag": True,
            "anomalous_transactions": [
                {"id": "TX-HIGH-01", "amount": 9850, "note": "series of threshold-adjacent transfers"},
                {"id": "TX-HIGH-02", "amount": 9900, "note": "rapid offshore onward transfer"},
            ],
            "typology_hits": ["Structuring below reporting threshold", "Rapid offshore layering activity"],
            "transaction_risk_score": 50,
        },
    },
    ("wirecard ag", "corporate", "DE"): {
        "identity": {
            "registry_match": True,
            "ocr_documents": 0,
            "discrepancies": [],
            "identity_score": 92,
            "verified_fields": ["name"],
        },
        "screening": {
            "sanctions_hit": False,
            "adverse_media_hit": True,
            "pep_hit": False,
            "findings": [
                {
                    "type": "adverse_media",
                    "match": "Public coverage highlights accounting irregularities and insolvency proceedings.",
                    "confidence": 0.91,
                    "foundry_iq_citation": {
                        "knowledge_base": "argus-kb-adversemedia",
                        "document": "wirecard_public_enforcement_summary.json",
                        "snippet_id": "demo-public-001",
                        "published_at": "2020-06-25",
                        "tags": ["fraud", "accounting", "governance"],
                    },
                }
            ],
            "screening_risk_score": 72,
            "foundry_iq_queries": 1,
        },
        "corporate": {
            "registry": {"found": True, "record": {"name": "Wirecard AG", "jurisdiction": "DE"}},
            "ubo_chain": {
                "ownership_chain": [{"name": "Wirecard AG", "jurisdiction": "DE"}],
                "depth": 1,
            },
            "jurisdiction_info": {"fatf_risk_tier": "standard"},
            "risk_flags": ["Public adverse-media profile warrants enhanced governance review"],
            "corporate_score": 60,
        },
        "transaction": {
            "transaction_count": 14,
            "date_range": {"from": "2026-01-08", "to": "2026-05-30"},
            "structuring_flag": False,
            "layering_flag": False,
            "anomalous_transactions": [],
            "typology_hits": [],
            "transaction_risk_score": 15,
        },
    },
    ("danske bank a/s", "corporate", "DK"): {
        "identity": {
            "registry_match": True,
            "ocr_documents": 0,
            "discrepancies": [],
            "identity_score": 94,
            "verified_fields": ["name"],
        },
        "screening": {
            "sanctions_hit": False,
            "adverse_media_hit": True,
            "pep_hit": False,
            "findings": [
                {
                    "type": "adverse_media",
                    "match": "Public coverage references historical AML control weaknesses and supervisory scrutiny.",
                    "confidence": 0.88,
                    "foundry_iq_citation": {
                        "knowledge_base": "argus-kb-adversemedia",
                        "document": "danske_bank_public_enforcement_summary.json",
                        "snippet_id": "demo-public-002",
                        "published_at": "2018-09-19",
                        "tags": ["aml", "controls", "governance"],
                    },
                }
            ],
            "screening_risk_score": 68,
            "foundry_iq_queries": 1,
        },
        "corporate": {
            "registry": {"found": True, "record": {"name": "Danske Bank A/S", "jurisdiction": "DK"}},
            "ubo_chain": {
                "ownership_chain": [{"name": "Danske Bank A/S", "jurisdiction": "DK"}],
                "depth": 1,
            },
            "jurisdiction_info": {"fatf_risk_tier": "low"},
            "risk_flags": ["Legacy controls issue requires remediation evidence review"],
            "corporate_score": 58,
        },
        "transaction": {
            "transaction_count": 18,
            "date_range": {"from": "2026-01-22", "to": "2026-05-26"},
            "structuring_flag": False,
            "layering_flag": False,
            "anomalous_transactions": [],
            "typology_hits": [],
            "transaction_risk_score": 18,
        },
    },
    ("westpac banking corporation", "corporate", "AU"): {
        "identity": {
            "registry_match": True,
            "ocr_documents": 0,
            "discrepancies": [],
            "identity_score": 93,
            "verified_fields": ["name"],
        },
        "screening": {
            "sanctions_hit": False,
            "adverse_media_hit": True,
            "pep_hit": False,
            "findings": [
                {
                    "type": "adverse_media",
                    "match": "Public coverage references AML and sanctions-screening control failings.",
                    "confidence": 0.87,
                    "foundry_iq_citation": {
                        "knowledge_base": "argus-kb-adversemedia",
                        "document": "westpac_public_enforcement_summary.json",
                        "snippet_id": "demo-public-003",
                        "published_at": "2020-11-24",
                        "tags": ["aml", "sanctions", "monitoring"],
                    },
                }
            ],
            "screening_risk_score": 66,
            "foundry_iq_queries": 1,
        },
        "corporate": {
            "registry": {"found": True, "record": {"name": "Westpac Banking Corporation", "jurisdiction": "AU"}},
            "ubo_chain": {
                "ownership_chain": [{"name": "Westpac Banking Corporation", "jurisdiction": "AU"}],
                "depth": 1,
            },
            "jurisdiction_info": {"fatf_risk_tier": "standard"},
            "risk_flags": ["Public compliance remediation case requires control evidence"],
            "corporate_score": 57,
        },
        "transaction": {
            "transaction_count": 20,
            "date_range": {"from": "2026-02-01", "to": "2026-05-29"},
            "structuring_flag": False,
            "layering_flag": False,
            "anomalous_transactions": [],
            "typology_hits": [],
            "transaction_risk_score": 20,
        },
    },
}