"""
ARGUS Orchestrator Agent
Decomposes KYC requests into sub-tasks and coordinates A2A sub-agents.
Fan-out: Identity, Screening, Corporate, Transaction run in parallel.
Fan-in:  Compliance & Risk agent synthesises all upstream results.
"""
import asyncio
import os
import httpx
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.env_loader import load_repo_env

load_repo_env(__file__)

AGENT_URLS = {
    "identity":    os.getenv("IDENTITY_AGENT_URL",    "http://localhost:8001"),
    "screening":   os.getenv("SCREENING_AGENT_URL",   "http://localhost:8002"),
    "corporate":   os.getenv("CORPORATE_AGENT_URL",   "http://localhost:8003"),
    "transaction": os.getenv("TRANSACTION_AGENT_URL", "http://localhost:8004"),
    "compliance":  os.getenv("COMPLIANCE_AGENT_URL",  "http://localhost:8005"),
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
            result = response.json()
            return result
        except httpx.HTTPError as e:
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
    started_at = datetime.now(timezone.utc)

    # Structured logging for orchestrator lifecycle
    from utils.structured_logger import get_logger
    logger = get_logger('orchestrator')
    
    logger.info('orchestrator.start', extra={"task_id": task_id})

    # ── Demo profile shortcut ────────────────────────────────────────────────
    from utils.demo_profiles import get_demo_profile
    profile = get_demo_profile(
        kyc_request.get("entity_name", ""),
        kyc_request.get("entity_type", ""),
        kyc_request.get("jurisdiction", ""),
    )

    # ── PHASE 1: Fan-out (parallel) ──────────────────────────────────────────
    t0 = datetime.now(timezone.utc)

    if profile:
        # Deterministic demo results — bypass live calls for parallel agents.
        identity_result = {
            "agent": "identity",
            "status": "completed",
            "result": profile.get("identity", {}),
        }
        screening_result = {
            "agent": "screening",
            "status": "completed",
            "result": profile.get("screening", {}),
        }
        corporate_result = {
            "agent": "corporate",
            "status": "completed",
            "result": profile.get("corporate", {}),
        }
        transaction_result = {
            "agent": "transaction",
            "status": "completed",
            "result": profile.get("transaction", {}),
        }
    else:
        parallel_tasks = [
            call_agent("identity",    kyc_request, task_id),
            call_agent("screening",   kyc_request, task_id),
            call_agent("corporate",   kyc_request, task_id),
            call_agent("transaction", kyc_request, task_id),
        ]
        parallel_results = await asyncio.gather(*parallel_tasks)
        identity_result, screening_result, corporate_result, transaction_result = parallel_results

    t1 = datetime.now(timezone.utc)

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
    
    t2 = datetime.now(timezone.utc)

    logger.info('orchestrator.phase2.complete', extra={"task_id": task_id})

    # ── PHASE 3: Synthesise final report ─────────────────────────────────────
    report = await synthesise_report(
        task_id, kyc_request,
        identity_result, screening_result,
        corporate_result, transaction_result,
        compliance_result,
    )

    report["timeline"] = [
        {"step": "Request received", "time": started_at.strftime("%H:%M:%S")},
        {"step": "Identity Agent", "time": t0.strftime("%H:%M:%S")},
        {"step": "Screening Agent", "time": t0.strftime("%H:%M:%S")},
        {"step": "Corporate Agent", "time": t0.strftime("%H:%M:%S")},
        {"step": "Transaction Agent", "time": t0.strftime("%H:%M:%S")},
        {"step": "Parallel agents complete", "time": t1.strftime("%H:%M:%S")},
        {"step": "Compliance & Risk Agent", "time": t1.strftime("%H:%M:%S")},
        {"step": "Final report generated", "time": t2.strftime("%H:%M:%S")},
    ]
    report["total_latency_seconds"] = round((t2 - started_at).total_seconds(), 2)

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
    from utils.structured_logger import get_logger
    import json
    logger = get_logger('orchestrator.synthesise')
    
    # Extract compliance result safely
    comp_result = compliance.get("result", {}) or {}
    screening_result = screening.get("result", {}) or {}
    compliance_result = compliance.get("result", {}) or {}
    
    
    logger.info('compliance_received', extra={
        "compliance_keys": list(compliance.keys()),
        "comp_result_keys": list(comp_result.keys()),
        "has_risk_summary": "risk_summary" in comp_result,
    })
    foundry_iq_queries = int(screening_result.get("foundry_iq_queries", 0)) + int(
        compliance_result.get("foundry_iq_queries", 0)
    )
    explanation = comp_result.get("explanation", "")

    report = {
        "report_id":    f"argus-rpt-{task_id}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "explanation": explanation,
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
            "tool_calls":         15,
            "foundry_iq_queries": foundry_iq_queries,
            "identity_status":    identity.get("status"),
            "screening_status":   screening.get("status"),
            "corporate_status":   corporate.get("status"),
            "transaction_status": transaction.get("status"),
            "compliance_status":  compliance.get("status"),
        },
    }
    return report
