# Roadmap: accessibility

**Status:** partly done. Revised 2026-11-11.
**Goal:** every ARGUS screen meets WCAG 2.2 Level AA, confirmed with assistive technology and
not only with automated checks.

## Done (the web UI in `web/`)

- Light and dark themes follow the system setting; every declared text and background colour
  pair passes WCAG AA in both, checked in CI.
- Risk badges use the audited palette in `src/argus/accessibility/wcag.py`, and the tier is
  always written out, never shown by colour alone.
- Landmarks, a skip link, one `h1` per page and a heading for every report section.
- Labelled form fields; form errors in an alert region.
- A polite live region announces progress while the agents run.
- Visible keyboard focus; wide tables scroll from the keyboard.
- `prefers-reduced-motion` stops the spinner and transitions.
- axe finds no WCAG 2.2 AA violations on any page, in light, dark and phone layouts
  (end-to-end tests).

Badge contrast, white text on the tier colour: HIGH `#c0392b` 5.44:1, MEDIUM `#a16207` 4.92:1,
LOW `#1e8449` 4.72:1 (all AA), CRITICAL `#8e1a0e` 9.11:1 (AAA).

## Not done

- No review with screen readers or other assistive technology. Automated checks find only some
  problems, so this is not a full audit.
- No high-contrast mode. A possible design: a stored user preference that switches to a
  black-and-white palette with tier colours chosen to pass AA on black.
- No check of the brand and architecture images beyond text contrast.

## Where the checks are

- `src/argus/accessibility/wcag.py`: contrast ratio and palette audit.
- `tests/test_accessibility.py`: palette checks in CI, including the web UI's risk colours.
- `scripts/ci/render_assets.py --check`: contrast of the stylesheet and the image masters.
- `web/e2e/`: axe on every page.
