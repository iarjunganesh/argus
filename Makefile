.PHONY: install lint format typecheck test docs check generate-data generate-ocr-docs upload-data index-knowledge-bases run-api run-ui

# Thin wrappers around uv for macOS/Linux. On Windows, run the same `uv run ...` commands directly.

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check . --fix

typecheck:
	uv run mypy agents api utils accessibility community ui config.py

test:
	uv run pytest --cov

docs:
	uv run python scripts/check_docs.py

# Everything CI runs, except the dependency audit and secret scan.
check: lint typecheck test docs

generate-data:
	uv run python data/synthetic/generate_entities.py
	uv run python data/synthetic/generate_corporate_graph.py
	uv run python data/synthetic/generate_transactions.py
	uv run python data/synthetic/generate_sanctions.py
	uv run python data/synthetic/generate_adverse_media.py

generate-ocr-docs:
	uv run python data/synthetic/generate_ocr_documents.py

upload-data:
	uv run python data/synthetic/upload_to_cosmos.py

index-knowledge-bases:
	uv run python foundry_iq/create_knowledge_bases.py
	uv run python foundry_iq/index_regulations.py
	uv run python data/public/generate_adverse_media_public.py
	uv run python foundry_iq/index_sanctions_and_media.py

run-api:
	uv run uvicorn api.main:app --host 127.0.0.1 --port 8000

run-ui:
	uv run python ui/gradio_app.py
