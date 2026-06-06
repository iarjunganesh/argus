# ARGUS Release Checklist (v0.1.0-hackathon)

Date: 2026-06-06

## Code & Repo

- [x] All recent feature/fix commits pushed to `origin/main`
- [x] Working tree clean before tag
- [x] Release tag created (`v0.1.0-hackathon`)

## Data & Indexing

- [x] Synthetic data generated
- [x] Cosmos DB upload completed
- [x] Azure AI Search indexes created and populated

## Runtime Verification

- [x] API gateway starts on `127.0.0.1:8000`
- [x] All 5 agent services start on `8001-8005`
- [x] Aggregated health endpoint returns `ok` for all agents (`/api/v1/admin/health`)
- [x] Smoke KYC assessment succeeds end-to-end

## Demo Assets

- [x] Demo runbook added (`docs/DEMO_RUNBOOK.md`)
- [x] Demo helper script added (`scripts/record_demo.ps1`)
- [x] Batch runner added and hardened (`scripts/batch_run_kyc.py`)
- [x] Batch sample reports generated (`data/reports_batch.jsonl`)

## Notes

- For stable batch runs, use API without hot reload:
  - `python -m uvicorn api.main:app --port 8000`
- If Azure RBAC blocks Cosmos access, some tools may fall back to mocks.
