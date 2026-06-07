"""
ARGUS API Gateway — FastAPI
Accepts KYC requests and routes to the Orchestrator.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from api.schemas import KYCRequest, StatusResponse
import uuid
from utils.structured_logger import get_logger

logger = get_logger('api.gateway')

app = FastAPI(
    title="ARGUS — Agentic KYC Risk Assessment",
    description="Multi-agent KYC system powered by Azure AI Foundry + Foundry IQ",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for demo (replace with Cosmos DB in production)
_reports: dict = {}
_status:  dict = {}


@app.get("/")
def root():
    logger.info('root', extra={"service": "ARGUS", "status": "running"})
    return {"service": "ARGUS", "status": "running", "version": "0.1.0"}


@app.post("/api/v1/kyc/assess", response_model=dict)
async def assess(request: KYCRequest, background_tasks: BackgroundTasks):
    """Submit a KYC request. Returns report_id immediately; assessment runs async."""
    report_id = f"argus-rpt-{uuid.uuid4().hex[:12]}"
    _status[report_id] = "processing"

    logger.info('kyc.request.submitted', extra={"report_id": report_id, "entity": request.entity_name})
    background_tasks.add_task(_run_assessment, report_id, request.dict())
    return {"report_id": report_id, "status": "processing"}


@app.get("/api/v1/kyc/report/{report_id}")
def get_report(report_id: str):
    if report_id not in _reports:
        status = _status.get(report_id, "not_found")
        raise HTTPException(status_code=404, detail=f"Report not found. Status: {status}")
    return _reports[report_id]


@app.get("/api/v1/kyc/status/{report_id}", response_model=StatusResponse)
def get_status(report_id: str):
    return StatusResponse(
        report_id=report_id,
        status=_status.get(report_id, "not_found"),
    )


@app.get("/api/v1/admin/agents")
def list_agents():
    """List all registered A2A sub-agents and their health."""
    import os
    agents = ["identity", "screening", "corporate", "compliance", "transaction"]
    return {
        "agents": [
            {
                "name":     a,
                "endpoint": os.getenv(f"{a.upper()}_AGENT_URL", f"http://localhost:800{i+1}"),
                "status":   "registered",
            }
            for i, a in enumerate(agents)
        ]
    }


@app.get('/api/v1/admin/health')
def aggregated_health():
    """Call each agent's /health endpoint and return an aggregated view.

    This is a lightweight, best-effort endpoint for local demos. It will
    attempt to GET /health on the default agent ports and report back.
    """
    import httpx

    agents = [
        ('identity', 'http://127.0.0.1:8001/health'),
        ('screening', 'http://127.0.0.1:8002/health'),
        ('corporate', 'http://127.0.0.1:8003/health'),
        ('compliance', 'http://127.0.0.1:8004/health'),
        ('transaction', 'http://127.0.0.1:8005/health'),
    ]
    results = {}
    for name, url in agents:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                results[name] = {'status': 'ok', 'info': r.json()}
            else:
                results[name] = {'status': 'error', 'code': r.status_code}
        except httpx.HTTPError as e:
            results[name] = {'status': 'unreachable', 'error': str(e)}

    logger.info('health.aggregated', extra={'agents': list(results.keys())})
    return {'aggregated': results}


async def _run_assessment(report_id: str, kyc_request: dict):
    """Background task: runs the full orchestration and stores result."""
    try:
        from agents.orchestrator.agent import run_kyc_assessment
        logger.info('kyc.assessment.start', extra={"report_id": report_id})
        report = await run_kyc_assessment(kyc_request)
        report["report_id"] = report_id
        _reports[report_id] = report
        _status[report_id]  = "completed"
        logger.info('kyc.assessment.completed', extra={"report_id": report_id})
    except Exception as e:
        _status[report_id] = "error"
        _reports[report_id] = {"report_id": report_id, "error": str(e), "status": "error"}
        logger.exception('kyc.assessment.error', extra={"report_id": report_id, "error": str(e)})
