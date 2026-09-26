"""Recorded demo profiles and the name aliases that resolve to them."""


def test_public_demo_profile_is_available():
    from argus.utils.demo_profiles import get_demo_profile

    profile = get_demo_profile("Wirecard AG", "corporate", "DE")
    assert profile is not None
    assert profile["screening"]["adverse_media_hit"] is True
    assert (
        profile["screening"]["findings"][0]["citation"]["document"]
        == "wirecard_public_enforcement_summary.json"
    )


def test_demo_profile_aliases_resolve_to_canonical_profiles():
    from argus.utils.demo_profiles import get_demo_profile

    wirecard = get_demo_profile("Wirecard", "corporate", "DE")
    cayman = get_demo_profile("Cayman Holdings", "corporate", "US")
    synthetic = get_demo_profile("Synthetic Holdings", "corporate", "US")
    jane = get_demo_profile("Jane Doe", "individual", "US")

    assert wirecard is not None and wirecard["screening"]["adverse_media_hit"] is True
    assert cayman is not None and cayman["screening"]["sanctions_hit"] is True
    assert synthetic is not None and synthetic["screening"]["pep_hit"] is True
    assert jane is not None and jane["screening"]["screening_risk_score"] == 5
