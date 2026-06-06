"""
ARGUS Orchestrator Agent
Decomposes KYC requests into sub-tasks and coordinates A2A sub-agents.
Fan-out: Identity, Screening, Corporate, Transaction run in parallel.
Fan-in:  Compliance & Risk agent synthesises all upstream results.
"""
import asyncio
import os
import httpx
from typing import Any
from dotenv import load_dotenv
from config import get_llm_client, MODEL_NAME

load_dotenv()

AGENT_URLS = {
    "identity":    os.getenv("IDENTITY_AGENT_URL",    "http://localhost:8001"),
    "screening":   os.getenv("SCREENING_AGENT_URL",   "http://localhost:8002"),
    "corporate":   os.getenv("CORPORATE_AGENT_URL",   "http://localhost:8003"),
    "transaction": os.getenv("TRANSACTION_AGENT_URL", "http://localhost:8005"),
    "compliance":  os.getenv("COMPLIANCE_AGENT_URL",  "http://localhost:8004"),
}

SYSTEM_PROMPT = """
You are ARGUS Orchestrator, a financial compliance reasoning agent.
You coordinate specialist agents to perform a complete KYC assessment.
You reason step-by-step, cite evidence from each agent's findings,
and produce a structured, auditable risk decision.
You never hallucinate regulatory rules — cite only what the Compliance
Agent has retrieved from the Foundry IQ regulations knowledge base.
All citations must include the source document and knowledge base reference.
"""


async def call_agent(agent_name: str, payload: dict, task_id: str) -> dict:
    """Send an A2A request to a sub-agent and return its result."""
    url = f"{AGENT_URLS[agent_name]}/a2a/invoke"
    message = {
        "a2a_version": "1.0",
        "source_agent": "argus-orchestrator-v1",
        "target_agent": f"argus-{agent_name}-agent-v1",
        "task_id": task_id,
        "payload": payload,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=message)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Graceful degradation: flag agent unavailable, continue
            return {
                "agent": agent_name,
                "status": "error",
                "error": str(e),
                "result": None,
            }


async def run_kyc_assessment(kyc_request: dict) -> dict:
    """
    Main orchestration entry point.
    1. Fan-out: call Identity, Screening, Corporate, Transaction in parallel
    2. Fan-in:  pass all results to Compliance & Risk agent
    3. Synthesise final risk report
    """
    import uuid
    task_id = f"kyc-{uuid.uuid4().hex[:12]}"

    # Structured logging for orchestrator lifecycle
    from utils.structured_logger import get_logger
    logger = get_logger('orchestrator')
    logger.info('orchestrator.start', extra={"task_id": task_id})

    # ── PHASE 1: Fan-out (parallel) ──────────────────────────────────────────
    parallel_tasks = [
        call_agent("identity",    kyc_request, task_id),
        call_agent("screening",   kyc_request, task_id),
        call_agent("corporate",   kyc_request, task_id),
        call_agent("transaction", kyc_request, task_id),
    ]
    parallel_results = await asyncio.gather(*parallel_tasks)
    identity_result, screening_result, corporate_result, transaction_result = parallel_results

    logger.info('orchestrator.phase1.complete', extra={"task_id": task_id})

    # ── PHASE 2: Fan-in — Compliance agent gets everything ───────────────────
    compliance_payload = {
        **kyc_request,
        "upstream_results": {
            "identity":    identity_result,
            "screening":   screening_result,
            "corporate":   corporate_result,
            "transaction": transaction_result,
        },
    }
    compliance_result = await call_agent("compliance", compliance_payload, task_id)

    logger.info('orchestrator.phase2.complete', extra={"task_id": task_id})

    # ── PHASE 3: Synthesise final report ─────────────────────────────────────
    report = await synthesise_report(
        task_id, kyc_request,
        identity_result, screening_result,
        corporate_result, transaction_result,
        compliance_result,
    )

    return report


async def synthesise_report(
    task_id: str,
    kyc_request: dict,
    identity: dict,
    screening: dict,
    corporate: dict,
    transaction: dict,
    compliance: dict,
) -> dict:
    """Use LLM to synthesise agent results into a final risk report narrative."""
    from datetime import datetime

    # Extract compliance result safely
    comp_result = compliance.get("result", {}) or {}

    report = {
        "report_id":    f"argus-rpt-{task_id}",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "entity": {
            "name":         kyc_request.get("entity_name"),
            "type":         kyc_request.get("entity_type"),
            "jurisdiction": kyc_request.get("jurisdiction"),
        },
        "risk_summary":       comp_result.get("risk_summary", {}),
        "dimension_scores":   comp_result.get("dimension_scores", {}),
        "key_findings":       comp_result.get("key_findings", []),
        "regulatory_triggers":comp_result.get("regulatory_triggers", []),
        "recommended_actions":comp_result.get("recommended_actions", []),
        "audit_trace": {
            "task_id":            task_id,
            "agents_invoked":     ["identity", "screening", "corporate", "transaction", "compliance"],
            "identity_status":    identity.get("status"),
            "screening_status":   screening.get("status"),
            "corporate_status":   corporate.get("status"),
            "transaction_status": transaction.get("status"),
            "compliance_status":  compliance.get("status"),
        },
    }
    return report
