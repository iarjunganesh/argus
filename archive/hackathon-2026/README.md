# Archive: Microsoft Agents League 2026 submission

This folder freezes the material written for the Microsoft Agents League — AI Skills Fest 2026
hackathon, where ARGUS was selected as one of three **Hack for Good** winners.

**Nothing here is maintained.** These files describe ARGUS as it was submitted in June 2026,
including claims that later reviews found overstated (for example, Semantic Kernel was listed as
a dependency but never imported). Current documentation lives in [`docs/`](../../docs/).

## Submitted state

The judged submission corresponds to commit `f606815` (2026-06-11).

## Former release tags

The project's versioning restarted at `v0.1.0`, and the v1 tags were deleted on 2026-09-26. They are
listed here so that any of them can be re-created with `git tag <name> <commit>`.

| Tag | Tagged commit | Notes |
| --- | --- | --- |
| `v1.2.0` | `20e056b` | |
| `v1.3.0` | `74ddbba` | Annotated: "demo freeze release with UI/storytelling alignment" |
| `v1.4.0` | `974f5ac` | |
| `v1.5.0` | `f606815` | Annotated. **The submitted state.** |
| `v1.6.0` | `9aee081` | Annotated: "accurate award framing, restructured badges, v2 roadmap scaffolding". Pointed to a pre-merge commit on no branch; its tree is identical to `d2c9380` on `main`, so re-create it there. |

## Contents

| Path | What it is |
| --- | --- |
| `submission/` | Final demo runbook, narration script, and the educator blog post |
| `docs/ARGUS_Architecture.md` | The original architecture and design spec, written around the judging criteria |
| `docs/DEMO_RUNBOOK.md`, `docs/START_GRADIO.md` | How the demo stack was started and recorded |
| `docs/ARGUS_IQ_Prereq_CrossRef.md` | Cross-reference to the IQ Series prerequisite work |
| `CHANGELOG-v1.md` | The changelog from `v0.1.0-hackathon` to `v1.5.0` (`v1.6.0` never got an entry) |
| `RELEASE_CHECKLIST.md` | The `v0.1.0-hackathon` release checklist |
| `assets/` | Slide deck, opening and closing slides, the Wirecard AG demo screenshots, and the hackathon-era brand: the pentagon logo (`argus.svg`, `argus.png`), the 1300×500 banner, the Mermaid architecture sources and the animated architecture GIFs |
| `scripts/record_demo.ps1` | The demo recording helper |
| `scripts/build_animated_diagram.py`, `scripts/capture_gif_frames.js` | How the hackathon architecture GIFs were made (superseded by `scripts/render_assets.py`) |
