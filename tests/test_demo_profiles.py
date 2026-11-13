"""Recorded demo profiles and the name aliases that resolve to them."""

import pytest

from argus.agents.corporate.tools.jurisdiction_mapper import FATF_HIGH_RISK
from argus.utils.demo_profiles import (
    DEMO_PROFILES,
    SYNTHETIC_DEMO_CASES,
    get_demo_profile,
    is_synthetic_demo_case,
)

STAND_INS = (
    ("synthetic payments ag", "corporate", "DE"),
    ("synthetic nordic bank a/s", "corporate", "DK"),
    ("synthetic pacific banking corporation", "corporate", "AU"),
)


def test_stand_in_profile_is_available():
    profile = get_demo_profile("Synthetic Payments AG", "corporate", "DE")
    assert profile is not None
    assert profile["screening"]["adverse_media_hit"] is True
    assert (
        profile["screening"]["findings"][1]["citation"]["document"]
        == "synthetic_payments_accounts_inquiry.json"
    )


def test_demo_profile_aliases_resolve_to_canonical_profiles():
    cayman = get_demo_profile("Cayman Holdings", "corporate", "US")
    synthetic = get_demo_profile("Synthetic Holdings", "corporate", "US")
    jane = get_demo_profile("Jane Doe", "individual", "US")

    assert cayman is not None and cayman["screening"]["sanctions_hit"] is True
    assert synthetic is not None and synthetic["screening"]["pep_hit"] is True
    assert jane is not None and jane["screening"]["screening_risk_score"] == 5


def test_every_demo_case_is_synthetic():
    assert len(SYNTHETIC_DEMO_CASES) == len(DEMO_PROFILES) == 6
    for name, kind, code in SYNTHETIC_DEMO_CASES:
        assert (name.lower(), kind, code) in DEMO_PROFILES
        assert is_synthetic_demo_case(f" {name.upper()} ", kind.title(), code.lower())
    assert not is_synthetic_demo_case("Unlisted Synthetic GmbH", "corporate", "DE")
    assert not is_synthetic_demo_case("Jane Synthetic", "corporate", "DE")


@pytest.mark.parametrize("key", STAND_INS, ids=[name for name, _, _ in STAND_INS])
def test_stand_in_scores_follow_the_live_agents(key):
    """Each stand-in score is what its live agent computes from the recorded facts.

    The formulas restate `identity_validator`, and the scoring in the screening, corporate and
    transaction agents; a change there should change these profiles too.
    """
    profile = DEMO_PROFILES[key]

    identity = profile["identity"]
    severities = [d["severity"] for d in identity["discrepancies"]]
    assert identity["identity_score"] == max(
        0, 100 - 30 * severities.count("high") - 10 * severities.count("medium")
    )

    screening = profile["screening"]
    assert screening["screening_risk_score"] == min(
        60 * screening["sanctions_hit"] + 25 * screening["pep_hit"]
        + 15 * screening["adverse_media_hit"],
        100,
    )  # fmt: skip
    assert {f["type"] for f in screening["findings"]} == {
        kind
        for kind, hit in (
            ("sanctions", screening["sanctions_hit"]),
            ("pep", screening["pep_hit"]),
            ("adverse_media", screening["adverse_media_hit"]),
        )
        if hit
    }

    corporate = profile["corporate"]
    chain = corporate["ubo_chain"]["ownership_chain"]
    assert corporate["risk_flags"] == [
        f"High-risk jurisdiction node: {node['name']} ({node['jurisdiction']})"
        for node in chain
        if node["jurisdiction"] in FATF_HIGH_RISK
    ]
    depth_penalty = 10 if corporate["ubo_chain"]["depth"] > 3 else 0
    assert corporate["corporate_score"] == max(
        0, 100 - 15 * len(corporate["risk_flags"]) - depth_penalty
    )

    transaction = profile["transaction"]
    assert transaction["transaction_risk_score"] == min(
        40 * transaction["structuring_flag"] + 30 * transaction["layering_flag"]
        + 10 * len(transaction["typology_hits"]),
        100,
    )  # fmt: skip
