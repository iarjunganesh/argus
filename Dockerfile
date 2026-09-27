# syntax=docker/dockerfile:1
# The ARGUS API: one process that runs every agent through the orchestrator's workflow.
#   docker build -t argus .
#   docker run --rm -p 8000:8000 argus
# Base images are pinned by tag and digest; scripts/ci/check_versions.py checks the pins and the
# post-release dependency refresh moves them (docs/RELEASING.md).

FROM ghcr.io/astral-sh/uv:0.12.19@sha256:04d046b13e60d6bcec73cbc5e1cad25d680dea90c8573340950a0ac2d1aef424 AS uv

FROM python:3.14.7-slim-trixie@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
# Runtime dependencies only: no dependency groups (dev tools, Gradio, data generators, Tesseract).
# --no-build: wheels only, so no package's build script runs (the project itself still builds).
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-default-groups --no-install-project --no-editable --no-build
COPY src ./src
RUN uv sync --locked --no-default-groups --no-editable --no-build

FROM python:3.14.7-slim-trixie@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS runtime
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin argus
COPY --from=build /app/.venv /app/.venv
# The public demo data the local backend reads. Synthetic data is generated, never baked in:
# without it the local backend finds nothing and says so; deployments use the Azure backend.
COPY data/public/adverse_media_public.jsonl /app/data/public/adverse_media_public.jsonl
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    ARGUS_DATA_DIR=/app/data
WORKDIR /app
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --start-interval=2s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["uvicorn", "argus.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
