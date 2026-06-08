# Changelog

All notable changes to this project are documented in this file.

## [v1.2.0] - 2026-06-08

### Changed

- Refreshed Gradio report styling to use theme-safe neutral cards with semantic text accents for risk tiers across light and dark modes.
- Updated demo narration assets for a two-entity judge flow under five minutes.
- Updated architecture and README wording to align with synthetic core data plus public-source adverse-media summaries.
- Replaced the duplicate demo script with a single canonical voiceover asset and removed the stale script reference from docs indexes.
- Added a voiceover sync map and wait-window guidance so the sequence-diagram beat stays aligned with the narrated demo flow.
- Aligned the IQ prerequisite cross-reference and root README with the issued Global AI badge status.
- Removed the duplicate visible risk-tier banner in the Gradio report while keeping test compatibility markers in place.

### Documentation

- Consolidated submission workflow to a single canonical runbook: `docs/ARGUS_PreSubmission_Steps.md`.
- Removed archived duplicate runbooks:
  - `docs/ARGUS_FinalSteps.md`
  - `docs/ARGUS_NextSteps_June8-14.md`
  - `docs/ARGUS_Recording_Guide.md`
- Updated documentation index and root README references to point to the canonical runbook.

### Repository Hygiene

- Added `.gradio/` to `.gitignore` to prevent local UI artifacts from appearing in commits.

## [v0.1.0-hackathon] - 2026-06-06

### Added

- Structured JSON logging utility (`utils/structured_logger.py`)
- Agent `/health` endpoints for identity, screening, corporate, compliance, and transaction agents
- Aggregated health endpoint in API (`GET /api/v1/admin/health`)
- Demo runbook (`docs/DEMO_RUNBOOK.md`)
- Demo recording helper script (`scripts/record_demo.ps1`)
- Batch KYC runner (`scripts/batch_run_kyc.py`)
- Cosmos count checker script (`scripts/check_cosmos_counts.py`)
- Batch report artifact (`data/reports_batch.jsonl`)

### Changed

- Updated `README.md` with demo/testing and batch-run guidance
- Updated runbook commands to use stable API mode (without `--reload`) for batch runs
- Improved batch runner resilience:
  - submit retries
  - transient poll error handling
  - per-item failure logging to `data/reports_batch_errors.jsonl`

### Fixed

- Corporate graph generation edge case (`n=1` ownership split)
- Orchestrator indentation bug causing runtime failures
- Cosmos upload ID mapping and upload robustness
