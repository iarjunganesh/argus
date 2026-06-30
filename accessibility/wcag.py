"""
WCAG 2.1 color contrast utilities.

Implements the relative luminance and contrast ratio formulas from
https://www.w3.org/TR/WCAG21/#contrast-minimum (Success Criterion 1.4.3).
"""

from __future__ import annotations
from enum import Enum
import re


class WCAGLevel(Enum):
    AA = 4.5       # Normal text minimum
    AA_LARGE = 3.0 # Large text (18pt+ or 14pt bold)
    AAA = 7.0      # Enhanced


# Risk tier palette — these are what ARGUS renders for every report.
ARGUS_PALETTE = {
    "risk_low":       ("#2ecc71", "#ffffff"),
    "risk_medium":    ("#f39c12", "#ffffff"),
    "risk_high":      ("#e74c3c", "#ffffff"),
    "risk_critical":  ("#8e1a0e", "#ffffff"),
    "accent_blue":    ("#1d4ed8", "#ffffff"),
    "accent_teal":    ("#0f766e", "#ffffff"),
    "accent_amber":   ("#a16207", "#ffffff"),
    "subdued_text":   ("#64748b", "#ffffff"),
    "subdued_dark":   ("#475569", "#ffffff"),
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", hex_color):
        raise ValueError(f"Invalid hex color: #{hex_color}")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def _linearize(channel: int) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(foreground: str, background: str) -> float:
    l1 = relative_luminance(foreground)
    l2 = relative_luminance(background)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def assert_contrast_ratio(
    foreground: str,
    background: str,
    level: WCAGLevel = WCAGLevel.AA,
    label: str = "",
) -> float:
    """
    Raises AssertionError if the contrast ratio between foreground and background
    does not meet the given WCAG level. Returns the actual ratio on success.
    """
    ratio = contrast_ratio(foreground, background)
    tag = f" ({label})" if label else ""
    assert ratio >= level.value, (
        f"WCAG {level.name} failure{tag}: {foreground} on {background} "
        f"gives {ratio:.2f}:1, need {level.value}:1"
    )
    return ratio


def audit_palette(
    palette: dict[str, tuple[str, str]] | None = None,
    level: WCAGLevel = WCAGLevel.AA,
) -> dict[str, dict]:
    """
    Run a contrast audit over a palette dict of {label: (fg, bg)}.
    Returns per-token results with pass/fail and ratio.
    """
    palette = palette or ARGUS_PALETTE
    results = {}
    for label, (fg, bg) in palette.items():
        ratio = contrast_ratio(fg, bg)
        results[label] = {
            "foreground": fg,
            "background": bg,
            "ratio": round(ratio, 2),
            "passes": ratio >= level.value,
            "level": level.name,
        }
    return results
