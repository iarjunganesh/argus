.PHONY: install setup-azure generate-data generate-ocr-docs upload-data index-knowledge-bases run-api run-ui test lint clean

PYTHON := C:/Users/arjunganesh/AppData/Local/Programs/Python/Python314/python.exe

# ── Setup ─────────────────────────────────────
install:
	$(PYTHON) -m pip install -r requirements.txt

setup-azure:
	@echo "Provisioning Azure resources (requires Azure CLI login)..."
	powershell -ExecutionPolicy Bypass -File infra/setup.ps1

# ── Data ──────────────────────────────────────
generate-data:
	@echo "Generating synthetic datasets..."
	$(PYTHON) data/synthetic/generate_entities.py
	$(PYTHON) data/synthetic/generate_corporate_graph.py
	$(PYTHON) data/synthetic/generate_transactions.py
	$(PYTHON) data/synthetic/generate_sanctions.py
	$(PYTHON) data/synthetic/generate_adverse_media.py
	@echo "Done. Synthetic data ready in data/synthetic/"

generate-ocr-docs:
	@echo "Generating synthetic OCR documents and uploading to blob storage when configured..."
	$(PYTHON) data/synthetic/generate_ocr_documents.py
	@echo "Done. OCR documents ready in data/synthetic/ocr_documents/"

upload-data:
	@echo "Uploading synthetic data to Cosmos DB..."
	$(PYTHON) data/synthetic/upload_to_cosmos.py
	@echo "Done."

# ── Foundry IQ ────────────────────────────────
index-knowledge-bases:
	@echo "Indexing into Foundry IQ knowledge bases (Azure AI Search)..."
	$(PYTHON) foundry_iq/create_knowledge_bases.py
	$(PYTHON) foundry_iq/index_regulations.py
	$(PYTHON) data/public/generate_adverse_media_public.py
	$(PYTHON) foundry_iq/index_sanctions_and_media.py
	@echo "Done. Foundry IQ knowledge bases ready."
	@echo "Done. Foundry IQ knowledge bases ready."

# ── Run ───────────────────────────────────────
run-api:
	$(PYTHON) -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

run-ui:
	$(PYTHON) ui/gradio_app.py

run-all:
	@echo "Start API first: make run-api"
	@echo "Then UI: make run-ui"

# ── Agents (individual, for development) ──────
run-identity-agent:
	$(PYTHON) -m uvicorn agents.identity.agent:app --port 8001 --reload

run-screening-agent:
	$(PYTHON) -m uvicorn agents.screening.agent:app --port 8002 --reload

run-corporate-agent:
	$(PYTHON) -m uvicorn agents.corporate.agent:app --port 8003 --reload

run-transaction-agent:
	$(PYTHON) -m uvicorn agents.transaction.agent:app --port 8004 --reload

run-compliance-agent:
	$(PYTHON) -m uvicorn agents.compliance.agent:app --port 8005 --reload

# ── Test ──────────────────────────────────────
test:
	$(PYTHON) -m pytest --cov=agents --cov-report=term --cov-report=xml tests/ -v

test-agents:
	$(PYTHON) -m pytest tests/test_agents.py -v

test-tools:
	$(PYTHON) -m pytest tests/test_tools.py -v

# ── Lint ──────────────────────────────────────
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

# ── Clean ─────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -exec rm -rf {} +
