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

## Current state (the web UI in `web/`)

- ✅ Light and dark themes follow the system setting; every declared text/background colour pair passes WCAG AA in both, checked in CI
- ✅ Risk badges use the audited palette, and the tier is always written out (never colour alone)
- ✅ Landmarks, a skip link, one `h1` per page and a heading for every report section
- ✅ Labelled form fields; form errors in an alert region
- ✅ A polite live region announces progress while the agents run
- ✅ Visible keyboard focus; wide tables scroll from the keyboard
- ✅ `prefers-reduced-motion` stops the spinner and transitions
- ✅ axe finds no WCAG 2.2 AA violations on any page, in light, dark and phone layouts (end-to-end tests)
- ❌ No review yet with screen readers or other assistive technology, and no full audit
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
- `tests/test_accessibility.py` — CI-enforced palette checks, including the web UI's risk colours
- `web/e2e/` — axe checks of every page in the end-to-end tests
