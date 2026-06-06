.PHONY: install generate-data index-knowledge-bases run-api run-ui test lint clean

# ── Setup ─────────────────────────────────────
install:
	pip install -r requirements.txt

# ── Data ──────────────────────────────────────
generate-data:
	@echo "Generating synthetic datasets..."
	python data/synthetic/generate_entities.py
	python data/synthetic/generate_corporate_graph.py
	python data/synthetic/generate_transactions.py
	python data/synthetic/generate_sanctions.py
	python data/synthetic/generate_adverse_media.py
	@echo "Done. Synthetic data ready in data/synthetic/"

# ── Foundry IQ ────────────────────────────────
index-knowledge-bases:
	@echo "Indexing into Foundry IQ knowledge bases..."
	python foundry_iq/create_knowledge_bases.py
	python foundry_iq/index_regulations.py
	python foundry_iq/index_sanctions.py
	python foundry_iq/index_adverse_media.py
	@echo "Done. Foundry IQ knowledge bases ready."

# ── Run ───────────────────────────────────────
run-api:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

run-ui:
	python ui/gradio_app.py

run-all:
	@echo "Start API first: make run-api"
	@echo "Then UI: make run-ui"

# ── Agents (individual, for development) ──────
run-identity-agent:
	uvicorn agents.identity.agent:app --port 8001 --reload

run-screening-agent:
	uvicorn agents.screening.agent:app --port 8002 --reload

run-corporate-agent:
	uvicorn agents.corporate.agent:app --port 8003 --reload

run-compliance-agent:
	uvicorn agents.compliance.agent:app --port 8004 --reload

run-transaction-agent:
	uvicorn agents.transaction.agent:app --port 8005 --reload

# ── Test ──────────────────────────────────────
test:
	pytest tests/ -v

test-agents:
	pytest tests/test_agents.py -v

test-tools:
	pytest tests/test_tools.py -v

# ── Lint ──────────────────────────────────────
lint:
	ruff check .
	ruff format --check .

# ── Clean ─────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -exec rm -rf {} +
