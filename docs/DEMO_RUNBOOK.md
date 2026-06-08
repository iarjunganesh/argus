# ARGUS Demo Runbook

Quick steps to reproduce the demo used for the Microsoft Agents League submission.

1. Provision Azure resources (already done in this workspace using infra/main.bicep)

2. Populate synthetic data and upload to Cosmos DB (already executed):

   ```powershell
   python data/synthetic/generate_entities.py
   python data/synthetic/generate_corporate_graph.py
   python data/synthetic/generate_transactions.py
   python data/synthetic/generate_sanctions.py
   python data/synthetic/generate_adverse_media.py
   python data/synthetic/upload_to_cosmos.py
   ```

3. Generate synthetic OCR documents and upload them to blob storage:

   ```powershell
   make generate-ocr-docs
   ```

4. Create Search indexes (Foundry IQ KBs):

   ```powershell
   python infra/create_search_indexes.py
   python foundry_iq/index_sanctions_and_media.py
   python foundry_iq/index_regulations.py
   ```

4. Start services (recommended one-command startup):

   ```powershell
   .\scripts\start_demo.ps1
   ```

   This starts all agents, API, and Gradio.

   Manual startup (advanced):

   ```powershell
   # API gateway (recommended without --reload during batch runs)
   python -m uvicorn api.main:app --port 8000

   # Agents
   python -m uvicorn agents.identity.agent:app --port 8001 --reload
   python -m uvicorn agents.screening.agent:app --port 8002 --reload
   python -m uvicorn agents.corporate.agent:app --port 8003 --reload
   python -m uvicorn agents.transaction.agent:app --port 8004 --reload
   python -m uvicorn agents.compliance.agent:app --port 8005 --reload

   # UI
   python ui/gradio_app.py
   ```

   Stop all demo services:

   ```powershell
   .\scripts\end_demo.ps1
   ```

5. Health checks (each agent exposes `/health`):

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/health
   Invoke-RestMethod http://127.0.0.1:8002/health
   ```

6. Run a single KYC request (or use the UI):

   ```powershell
   Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/kyc/assess -Method Post -Body (ConvertTo-Json @{entity_name='Acme Widgets'; entity_type='corporate'; jurisdiction='SE'; include_transaction_analysis=$true}) -ContentType 'application/json'
   ```

7. Batch run (generate 10 reports and save them):

   ```powershell
   python scripts/batch_run_kyc.py --count 10 --out data/reports_batch.jsonl --poll-timeout 180
   ```

   If any request fails, inspect `data/reports_batch_errors.jsonl`.

Notes:
- Structured JSON logs are emitted to stdout by all agents and the API gateway (see `utils/structured_logger.py`).
- If agents cannot reach Azure (RBAC issues), the code falls back to local mocks and will still run the orchestrator for demo purposes.
