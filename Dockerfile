# syntax=docker/dockerfile:1
# The ARGUS API: one process that runs every agent through the orchestrator's workflow.
#   docker build -t argus .
#   docker run --rm -p 8000:8000 argus
# Base images are pinned by tag and digest; scripts/ci/check_versions.py checks the pins and the
# post-release dependency refresh moves them (docs/RELEASING.md).

FROM ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 AS uv

FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
# Runtime dependencies only: no dependency groups (dev tools, data generators, Tesseract).
# --no-build: wheels only, so no package's build script runs (the project itself still builds).
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-default-groups --no-install-project --no-editable --no-build
COPY src ./src
RUN uv sync --locked --no-default-groups --no-editable --no-build

FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS runtime
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin argus
COPY --from=build /app/.venv /app/.venv
# No data is baked in: synthetic data is generated, so the local backend finds nothing and says
# so (the recorded demo profiles still run); deployments use the Azure backend.
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    ARGUS_DATA_DIR=/app/data
WORKDIR /app
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --start-interval=2s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["uvicorn", "argus.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
