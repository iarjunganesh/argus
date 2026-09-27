"""
ARGUS API — FastAPI
Accepts KYC requests and runs each assessment in this process, through the orchestrator's
Agent Framework workflow.
"""

import asyncio
import os
import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent

from argus.api.schemas import KYCRequest, StatusResponse
from argus.data_plane import get_data_plane
from argus.utils.env_loader import load_repo_env
from argus.utils.structured_logger import get_logger

load_repo_env(__file__)  # before the CORS middleware reads ARGUS_CORS_ORIGINS

logger = get_logger("api.gateway")

app = FastAPI(
    title="ARGUS — Agentic KYC Risk Assessment",
    description="Multi-agent KYC risk screening with explainable, cited findings",
    version="0.1.0",
)


def cors_origins() -> list[str]:
    """Browser origins allowed to call the API, from `ARGUS_CORS_ORIGINS` (comma-separated).

    Empty by default: the Gradio UI calls the API from its own server, so no browser origin needs
    access until a web UI is deployed.
    """
    raw = os.getenv("ARGUS_CORS_ORIGINS", "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Last-Event-ID"],
)

# How often the progress stream checks the report store, and how long it stays open.
STREAM_POLL_SECONDS = 0.25
STREAM_MAX_SECONDS = 600.0


@app.get("/")
def root():
    logger.info("root", extra={"service": "ARGUS", "status": "running"})
    return {"service": "ARGUS", "status": "running", "version": "0.1.0"}


@app.get("/health")
def health():
    """Liveness: the process is up. The whole assessment workflow runs inside it."""
    return {"status": "ok"}


@app.post("/api/v1/kyc/assess", response_model=dict)
async def assess(request: KYCRequest, background_tasks: BackgroundTasks):
    """Submit a KYC request. Returns report_id immediately; assessment runs async."""
    report_id = f"argus-rpt-{uuid.uuid4().hex[:12]}"
    await get_data_plane().reports.save_status(report_id, "processing")

    logger.info(
        "kyc.request.submitted", extra={"report_id": report_id, "entity": request.entity_name}
    )
    background_tasks.add_task(_run_assessment, report_id, request.model_dump())
    return {"report_id": report_id, "status": "processing"}


@app.get("/api/v1/kyc/report/{report_id}")
async def get_report(report_id: str):
    reports = get_data_plane().reports
    report = await reports.report(report_id)
    if report is None:
        status = await reports.status(report_id) or "not_found"
        raise HTTPException(status_code=404, detail=f"Report not found. Status: {status}")
    return report


@app.get("/api/v1/kyc/status/{report_id}", response_model=StatusResponse)
async def get_status(report_id: str):
    status = await get_data_plane().reports.status(report_id)
    return StatusResponse(report_id=report_id, status=status or "not_found")


async def known_report(report_id: str) -> str:
    """The report ID, if an assessment was submitted under it (checked before any streaming)."""
    if await get_data_plane().reports.status(report_id) is None:
        raise HTTPException(status_code=404, detail="Report not found. Status: not_found")
    return report_id


@app.get("/api/v1/kyc/stream/{report_id}", response_class=EventSourceResponse)
async def stream_progress(
    report_id: Annotated[str, Depends(known_report)],
    last_event_id: Annotated[str | None, Header()] = None,
) -> AsyncIterator[ServerSentEvent]:
    """Follow an assessment as server-sent events.

    One `agent_started` and one `agent_completed` event per agent (the second carries the
    agent's `source` and any `fallbacks`), then one `status` event when the assessment has
    finished, after which the stream closes. Events already recorded are sent first, so a
    client that connects late misses nothing; a reconnecting client's `Last-Event-ID` resumes
    after the last event it received.
    """
    sent = int(last_event_id) + 1 if last_event_id and last_event_id.isdigit() else 0
    async for event in progress_events(report_id, sent):
        yield event


async def progress_events(report_id: str, sent: int = 0) -> AsyncIterator[ServerSentEvent]:
    """The report's progress events from index `sent` on, then its final status."""
    reports = get_data_plane().reports
    deadline = time.monotonic() + STREAM_MAX_SECONDS
    while True:
        # Status first: once it has left `processing`, every event is already recorded.
        status = await reports.status(report_id)
        events = await reports.events(report_id)
        for index, event in enumerate(events[sent:], start=sent):
            yield ServerSentEvent(data=event, event=event["type"], id=str(index))
        sent = max(sent, len(events))
        if status != "processing" or time.monotonic() >= deadline:
            # After the deadline the status is still `processing`; the client may reconnect.
            yield ServerSentEvent(
                data={"type": "status", "report_id": report_id, "status": status},
                event="status",
            )
            return
        await asyncio.sleep(STREAM_POLL_SECONDS)


async def _run_assessment(report_id: str, kyc_request: dict):
    """Background task: runs the full orchestration, recording its progress, and stores result."""
    reports = get_data_plane().reports

    async def record(event: dict) -> None:
        await reports.append_event(report_id, event)

    try:
        from argus.agents.orchestrator.agent import run_kyc_assessment

        logger.info("kyc.assessment.start", extra={"report_id": report_id})
        report = await run_kyc_assessment(kyc_request, on_event=record)
        report["report_id"] = report_id
        await reports.save_report(report_id, report)
        await reports.save_status(report_id, "completed")
        logger.info("kyc.assessment.completed", extra={"report_id": report_id})
    except Exception as e:
        await reports.save_status(report_id, "error")
        await reports.save_report(
            report_id, {"report_id": report_id, "error": str(e), "status": "error"}
        )
        logger.exception("kyc.assessment.error", extra={"report_id": report_id, "error": str(e)})
