"""
WCAG 2.1 AA compliance tests for the ARGUS palette.

These run in CI to catch any color changes that break contrast requirements.
"""

import pytest

from argus.accessibility.wcag import (
    ARGUS_PALETTE,
    WCAGLevel,
    assert_contrast_ratio,
    audit_palette,
    contrast_ratio,
)


def test_contrast_ratio_known_values():
    # Black on white: 21:1
    ratio = contrast_ratio("#000000", "#ffffff")
    assert abs(ratio - 21.0) < 0.1

    # White on white: 1:1
    ratio = contrast_ratio("#ffffff", "#ffffff")
    assert abs(ratio - 1.0) < 0.01


def test_audit_palette_returns_all_tokens():
    results = audit_palette(ARGUS_PALETTE)
    assert set(results.keys()) == set(ARGUS_PALETTE.keys())
    for result in results.values():
        assert "ratio" in result
        assert "passes" in result
        assert result["ratio"] > 0


def test_argus_risk_palette_aa_compliance():
    """Every audited palette pair must meet the normal-text AA threshold."""
    results = audit_palette(ARGUS_PALETTE, level=WCAGLevel.AA)
    failures = {k: v for k, v in results.items() if not v["passes"]}
    assert not failures, "WCAG AA failures: " + ", ".join(
        f"{k} ({v['ratio']}:1)" for k, v in failures.items()
    )


def test_critical_color_passes_aaa():
    # Verify the actual CRITICAL token, not a duplicate that could drift from the UI.
    ratio = contrast_ratio(*ARGUS_PALETTE["risk_critical"])
    assert ratio >= WCAGLevel.AAA.value, (
        f"CRITICAL color {ratio:.2f}:1 no longer meets AAA — don't lighten it"
    )


def test_high_contrast_palette_passes_aa():
    """The high-contrast mode palette (dark background) must pass AA."""
    high_contrast = {
        "hc_risk_high": ("#ff6666", "#000000"),
        "hc_risk_medium": ("#ffcc00", "#000000"),
        "hc_risk_low": ("#66ff66", "#000000"),
        "hc_risk_critical": ("#ff9999", "#000000"),
        "hc_foreground": ("#ffffff", "#000000"),
    }
    results = audit_palette(high_contrast, level=WCAGLevel.AA)
    failures = {k: v for k, v in results.items() if not v["passes"]}
    assert not failures, "High-contrast palette WCAG AA failures: " + ", ".join(
        f"{k} ({v['ratio']:.2f}:1)" for k, v in failures.items()
    )


def test_invalid_hex_is_rejected():
    with pytest.raises(ValueError, match="Invalid hex color"):
        contrast_ratio("#12345", "#ffffff")


def test_assert_contrast_ratio_returns_ratio_or_explains_failure():
    assert assert_contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)

    with pytest.raises(AssertionError, match=r"WCAG AAA failure \(muted\): #777777"):
        assert_contrast_ratio("#777777", "#ffffff", WCAGLevel.AAA, label="muted")
