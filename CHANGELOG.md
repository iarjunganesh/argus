# Changelog

All notable changes to ARGUS are recorded here. The format follows
[Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

An entry states **what became true and how it was checked**, not which files moved.

Versioning restarted at `v0.1.0` on 2026-09-26. The history of the hackathon releases
(`v0.1.0-hackathon` to `v1.6.0`) is kept in
[`archive/hackathon-2026/CHANGELOG-v1.md`](archive/hackathon-2026/CHANGELOG-v1.md), and the former tags
are listed in [`archive/hackathon-2026/README.md`](archive/hackathon-2026/README.md).

## [Unreleased]

### Added

- **An architecture page that matches the running code** (`docs/ARCHITECTURE.md`): processes,
  request flow, the demo-profile shortcut and every service fallback, checked against the code.
- **The v2 plan is public** (`docs/ARGUS-V2-PLAN.md`), with its starting evidence taken from the
  code review rather than from the old README.

### Changed

- **Hackathon material is archived, not deleted.** Submission runbooks, narration, slides, the
  original architecture spec and the v1 changelog moved to `archive/hackathon-2026/` with
  `git mv`, so their history is preserved.
- **Versioning restarted.** Tags `v1.2.0` to `v1.6.0` were deleted locally and on GitHub; each
  tag's commit is recorded in the archive README. The orphaned `v1.6.0` commit (`9aee081`) was
  checked to have a tree identical to `d2c9380` on `main` before deletion, so no content was lost.
- **The README describes the code as it is.** It adds a status table of what works live, what
  falls back to mock data, and what doesn't work, and removes claims the code didn't support
  (Semantic Kernel, the A2A protocol, Azure AI Foundry Agent Service, a runnable community
  edition, a passing WCAG example).

### Fixed

- **The test suite runs from the repository root.** The empty root `__init__.py` made pytest
  treat the parent directory as the import root. Checked: 50 passed, 1 xfailed.

### Removed

- **Generated files are no longer tracked:** `coverage.xml` and `data/reports_batch.jsonl`.

### Known issues

- **Foundry IQ queries never reach Foundry IQ.** `regulations_rag`, `sanctions_checker` and
  `adverse_media_scanner` call `AIProjectClient.knowledge_bases.query`, which does not exist in
  `azure-ai-projects` 1.0.0 or 2.6.1 (checked 2026-09-26). Every call falls back to mock results.
