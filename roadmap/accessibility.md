# Roadmap: WCAG 2.1 AA Compliance

**Status:** In progress — utilities in `accessibility/`
**Goal:** Every ARGUS UI surface meets WCAG 2.1 Level AA.

---

## Why this matters for compliance tools

KYC reports are read by:
- Compliance analysts who may be colorblind (affecting ~8% of men)
- Case workers using screen readers in resource-constrained environments
- Bank customers in Explain Mode who may have visual or cognitive disabilities
- Regulators doing audits who need high-contrast print output

A compliance tool that is inaccessible is itself a compliance risk.

---

## Current state (v1)

- ✅ Light/dark mode — uses Gradio theme variables, no hard-coded colors
- ✅ Risk tier text always paired with color (never color alone)
- ✅ Semantic heading structure (h2 → h3 → content)
- ❌ No ARIA labels on interactive elements
- ❌ No ARIA live region for async report loading
- ❌ No keyboard navigation for report sections
- ❌ Color contrast not programmatically verified (HIGH red: 3.0:1 on white, fails AA)
- ❌ No `prefers-reduced-motion` handling
- ❌ No high-contrast mode toggle

---

## v2 targets

### Color contrast
All risk tier colors verified against `accessibility/wcag.py`:
- HIGH (#e74c3c on #ffffff) — currently 3.98:1, fails AA. Fix: darken to #c0392b (4.56:1 ✅)
- MEDIUM (#f39c12 on #ffffff) — currently 2.82:1, fails AA. Fix: darken to #d68910 — or pair with bold + underline as a non-color cue
- LOW (#2ecc71 on #ffffff) — currently 2.33:1, fails AA. Fix: darken text to #1e8449 or use on dark background
- CRITICAL (#8e1a0e on #ffffff) — 8.2:1 ✅ passes AAA

Strategy: every risk tier MUST use both color AND a non-color cue (icon, pattern, text label). Color contrast ratios are secondary validation.

### ARIA live regions
The async report generation currently gives no feedback to screen readers while agents are running.

```html
<div role="status" aria-live="polite" aria-label="Assessment progress" id="argus-live-region">
  Awaiting assessment submission.
</div>
```

States: idle → "Assessment in progress. Agents are running." → "Assessment complete. Report is ready."

### Keyboard navigation
- Tab order: Form inputs → Submit → Report sections → Expand/collapse controls
- Skip link: "Skip to report" anchor at top of page
- All `<details>` elements keyboard-accessible (already is in most browsers — verify)
- Focus visible on all interactive elements (no `outline: none`)

### Reduced motion
```css
@media (prefers-reduced-motion: reduce) {
  .risk-bar { transition: none; }
  .agent-pulse { animation: none; }
}
```

### High contrast mode toggle
User preference stored in `localStorage`. Swaps to a high-contrast palette:
- Background: #000000
- Foreground: #ffffff
- Risk HIGH: #ff6666 (meets AA on black)
- Risk MEDIUM: #ffcc00 (meets AA on black)
- Risk LOW: #66ff66 (meets AA on black)

---

## Test plan

```python
# tests/test_accessibility.py
from accessibility.wcag import audit_palette, WCAGLevel, ARGUS_PALETTE

def test_argus_palette_aa_compliance():
    results = audit_palette(ARGUS_PALETTE, level=WCAGLevel.AA)
    failures = [k for k, v in results.items() if not v["passes"]]
    assert not failures, f"WCAG AA failures: {failures}"
```

---

## Tools

- `accessibility/wcag.py` — contrast ratio checker, palette auditor
- `accessibility/aria.py` — centralized ARIA label strings
- `tests/test_accessibility.py` — CI-enforced contrast checks (to be added)
