"""
Accessibility utilities for ARGUS — WCAG 2.1 AA compliance helpers.
"""

from .wcag import WCAGLevel, assert_contrast_ratio, contrast_ratio

__all__ = ["WCAGLevel", "assert_contrast_ratio", "contrast_ratio"]
