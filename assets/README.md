# Assets

Every image here is drawn from a hand-authored SVG **master**. The `-light` and `-dark` files
next to each master are generated from it; don't edit them by hand.

## Brand

The mark is an open eye inside a diamond. Argus Panoptes was the watchman of Greek myth, and the
name is also the acronym: **A**gentic **R**isk & **G**overnance **U**nified **S**creening.

| Master | Size | Use | Exports |
| --- | --- | --- | --- |
| [`brand/banner.svg`](brand/banner.svg) | 1200×320 | README header | light/dark SVG |
| [`brand/banner-16x9.svg`](brand/banner-16x9.svg) | 1920×1080 | Title card for articles, slides and video | light/dark SVG, PNG, GIF |
| [`brand/social-preview.svg`](brand/social-preview.svg) | 1280×640 | GitHub social preview | `social-preview-dark.png` |
| [`brand/logo.svg`](brand/logo.svg) | 640×540 | Stacked logo, transparent background | light/dark SVG |
| [`brand/logo-mark.svg`](brand/logo-mark.svg) | 240×240 | The mark alone: avatar, favicon, UI header | light/dark SVG |

The five nodes on the orbit stand for the five specialist agents. In the animated masters the
orbit swings 72° and back while the outer ring swings the other way, so every loop ends where it
began. The emblem geometry is repeated in each brand master; if you change it, change it in all
five.

The GitHub social preview can't be set from the repository: upload
`brand/social-preview-dark.png` under **Settings → General → Social preview**.

## Architecture

| Master | Shows | Exports |
| --- | --- | --- |
| [`architecture/system-overview.svg`](architecture/system-overview.svg) | The **current** runtime: processes, ports, the agent services and the Azure data plane, with each service marked "live or mock" or "mock today" | light/dark SVG, PNG |
| [`architecture/investigation-flow.svg`](architecture/investigation-flow.svg) | One KYC request end to end, with the scoring rules and weights as coded, and which steps are deterministic and which use a language model | light/dark SVG, PNG, GIF |
| [`architecture/v2-target.svg`](architecture/v2-target.svg) | The **planned** v2 runtime from [`docs/ARGUS-V2-PLAN.md`](../docs/ARGUS-V2-PLAN.md), labelled as not built | light/dark SVG, PNG |

The architecture diagrams describe the code, not the aspiration. When the code changes a port,
a fallback, a weight or a threshold, update the diagram in the same pull request.

## How the files are made

```sh
uv run python scripts/render_assets.py            # variants, then PNG/GIF exports
uv run python scripts/render_assets.py --check    # what CI runs
uv run python scripts/render_assets.py --no-raster
```

- **Why two variants.** Each master holds a light palette and a dark palette (between
  `/* PALETTE:LIGHT */` and `/* PALETTE:DARK */` markers). GitHub shows README images through
  `<img>`, where an SVG can't see the page's theme, so the README uses `<picture>` with the
  `-light` and `-dark` files.
- **Contrast is checked.** Each master lists its text/background colour pairs in a
  `/* CONTRAST ... */` comment. `--check` fails if any pair is below WCAG AA (4.5:1) in either
  theme, using [`accessibility/wcag.py`](../src/argus/accessibility/wcag.py).
- **Rasters are exports, not sources.** PNG and GIF files need a Chromium browser and ffmpeg,
  so CI doesn't build or check them. Re-run the script after changing a master and commit the
  exports with it.
- **Animation is decoration.** The first frame of every animated image carries its full
  meaning, and every animation duration divides the 6-second loop.

The hackathon-era images and the scripts that made them are in
[`archive/hackathon-2026/assets/`](../archive/hackathon-2026/assets/).
