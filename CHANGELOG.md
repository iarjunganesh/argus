# Changelog

All notable changes to this project are documented in this file.

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
