# Roadmap: WCAG 2.1 AA Compliance

**Status:** In progress — utilities in `src/argus/accessibility/`
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

- ✅ Light/dark surfaces use Gradio theme variables; risk and status badges use explicit audited color pairs
- ✅ Risk tier text always paired with color (never color alone)
- ✅ Semantic heading structure (h2 → h3 → content)
- ❌ No ARIA labels on interactive elements
- ❌ No ARIA live region for async report loading
- ❌ No keyboard navigation for report sections
- ✅ Shared palette and rendered risk/status badge contrast verified in CI; other UI surfaces still need an accessibility audit
- ❌ No `prefers-reduced-motion` handling
- ❌ No high-contrast mode toggle

---

## v2 targets

### Color contrast

Risk palette correction completed during cleanup. The shared pairs are checked against
`src/argus/accessibility/wcag.py`; white text on these badge backgrounds has the same ratio:

- HIGH (#c0392b with #ffffff) — 5.44:1, passes AA
- MEDIUM (#a16207 with #ffffff) — 4.92:1, passes AA
- LOW (#1e8449 with #ffffff) — 4.72:1, passes AA
- CRITICAL (#8e1a0e with #ffffff) — 9.11:1, passes AAA

Every risk tier retains a text label, so color is not its only cue. Non-color cues do not
replace the contrast requirement. Remaining work includes auditing all other UI surfaces.

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
from argus.accessibility.wcag import audit_palette, WCAGLevel, ARGUS_PALETTE


def test_argus_palette_aa_compliance():
    results = audit_palette(ARGUS_PALETTE, level=WCAGLevel.AA)
    failures = [k for k, v in results.items() if not v["passes"]]
    assert not failures, f"WCAG AA failures: {failures}"
```

---

## Tools

- `src/argus/accessibility/wcag.py` — contrast ratio checker, palette auditor
- `src/argus/accessibility/aria.py` — centralized ARIA label strings
- `tests/test_accessibility.py` and `tests/test_gradio_ui.py` — CI-enforced palette and rendered-badge contrast checks
