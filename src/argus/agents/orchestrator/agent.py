"""
ARGUS Orchestrator
Runs a KYC assessment as one in-process Microsoft Agent Framework workflow.
Fan-out: Identity, Screening, Corporate, Transaction run concurrently.
Fan-in:  Compliance & Risk agent synthesises all upstream results.

Every agent's start and finish is passed to `on_event` as it happens; the API stores these
events so a client can follow the assessment as server-sent events.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Never

from agent_framework import (
    Executor,
    SupportsAgentRun,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from argus.agents.compliance import agent as compliance_agent
from argus.agents.corporate import agent as corporate_agent
from argus.agents.identity import agent as identity_agent
from argus.agents.provenance import UNAVAILABLE, demo_provenance
from argus.agents.screening import agent as screening_agent
from argus.agents.transaction import agent as transaction_agent
from argus.data_plane import configured_backend
from argus.utils import demo_profiles
from argus.utils.structured_logger import get_logger

logger = get_logger("orchestrator")

type AgentFn = Callable[[dict, str], Awaitable[dict]]
type EventSink = Callable[[dict], Awaitable[None]]

# The four agents that run concurrently, then the one that receives all their results. Each
# name is looked up in its module when the step runs, so tests can replace an agent.
PARALLEL_AGENTS = ("identity", "screening", "corporate", "transaction")
AGENTS = (*PARALLEL_AGENTS, "compliance")
_MODULES = {
    "identity": identity_agent,
    "screening": screening_agent,
    "corporate": corporate_agent,
    "transaction": transaction_agent,
    "compliance": compliance_agent,
}
TIMELINE_LABELS = {
    "identity": "Identity Agent",
    "screening": "Screening Agent",
    "corporate": "Corporate Agent",
    "transaction": "Transaction Agent",
    "compliance": "Compliance & Risk Agent",
}


@dataclass(frozen=True)
class Assessment:
    """What every step receives: the request, and the recorded demo scenario if it has one."""

    task_id: str
    request: dict
    profile: dict | None


@dataclass(frozen=True)
class AgentOutcome:
    """One parallel agent's response, passed to the compliance step."""

    assessment: Assessment
    response: dict


async def call_agent(agent_name: str, payload: dict, task_id: str) -> dict:
    """Run one agent. An agent that raises is reported as unavailable; the others continue."""
    assess: AgentFn = _MODULES[agent_name].assess
    try:
        return await assess(payload, task_id)
    except Exception as e:
        logger.exception("agent.error", extra={"task_id": task_id, "agent": agent_name})
        return {
            "agent": agent_name,
            "status": "error",
            "source": UNAVAILABLE,
            "fallbacks": [],
            "error": str(e),
            "result": None,
        }


class _Dispatch(Executor):
    @handler
    async def start(self, assessment: Assessment, ctx: WorkflowContext[Assessment]) -> None:
        await ctx.send_message(assessment)


class _ParallelAgent(Executor):
    @handler
    async def run(self, assessment: Assessment, ctx: WorkflowContext[AgentOutcome, dict]) -> None:
        if assessment.profile is not None:
            # A recorded demo scenario: its result stands in for the agent's tools.
            response = {
                "agent": self.id,
                "task_id": assessment.task_id,
                "status": "completed",
                **demo_provenance(),
                "result": assessment.profile.get(self.id, {}),
            }
        else:
            response = await call_agent(self.id, assessment.request, assessment.task_id)
        await ctx.yield_output(response)
        await ctx.send_message(AgentOutcome(assessment, response))


class _Compliance(Executor):
    @handler
    async def run(self, outcomes: list[AgentOutcome], ctx: WorkflowContext[Never, dict]) -> None:
        assessment = outcomes[0].assessment
        payload = {
            **assessment.request,
            "upstream_results": {o.response["agent"]: o.response for o in outcomes},
        }
        await ctx.yield_output(await call_agent("compliance", payload, assessment.task_id))


def build_workflow() -> Workflow:
    """The assessment graph: dispatch → four agents in parallel → compliance."""
    dispatch = _Dispatch(id="dispatch")
    parallel: list[Executor | SupportsAgentRun] = [
        _ParallelAgent(id=name) for name in PARALLEL_AGENTS
    ]
    fan_in = _Compliance(id="compliance")
    return (
        WorkflowBuilder(
            name="argus-kyc-assessment",
            start_executor=dispatch,
            output_from=[fan_in],
            intermediate_output_from=parallel,
        )
        .add_fan_out_edges(dispatch, parallel)
        .add_fan_in_edges(parallel, fan_in)
        .build()
    )


async def run_kyc_assessment(kyc_request: dict, on_event: EventSink | None = None) -> dict:
    """
    Main orchestration entry point.
    1. Fan-out: Identity, Screening, Corporate, Transaction in parallel
    2. Fan-in:  all results to the Compliance & Risk agent
    3. Synthesise the final risk report
    """
    task_id = f"kyc-{uuid.uuid4().hex[:12]}"
    started_at = datetime.now(UTC)
    logger.info("orchestrator.start", extra={"task_id": task_id})

    profile = demo_profiles.get_demo_profile(
        kyc_request.get("entity_name", ""),
        kyc_request.get("entity_type", ""),
        kyc_request.get("jurisdiction", ""),
    )
    assessment = Assessment(task_id, kyc_request, profile)

    responses: dict[str, dict] = {}
    started: dict[str, datetime] = {}
    finished: dict[str, datetime] = {}
    async for event in build_workflow().run(assessment, stream=True):
        agent = event.executor_id
        if agent not in AGENTS:
            continue
        if event.type == "executor_invoked":
            started[agent] = datetime.now(UTC)
            await _emit(on_event, {"type": "agent_started", "agent": agent, "at": started[agent]})
        elif event.type in ("intermediate", "output"):
            responses[agent] = event.data
            finished[agent] = datetime.now(UTC)
            await _emit(
                on_event,
                {
                    "type": "agent_completed",
                    "agent": agent,
                    "at": finished[agent],
                    "status": event.data.get("status"),
                    "source": event.data.get("source"),
                    "fallbacks": event.data.get("fallbacks", []),
                },
            )

    logger.info("orchestrator.complete", extra={"task_id": task_id})
    report = await synthesise_report(task_id, kyc_request, *(responses[agent] for agent in AGENTS))
    completed_at = datetime.now(UTC)
    report["timeline"] = _timeline(started_at, started, finished, completed_at)
    report["total_latency_seconds"] = round((completed_at - started_at).total_seconds(), 2)
    return report


async def _emit(on_event: EventSink | None, event: dict) -> None:
    if on_event is not None:
        await on_event({**event, "at": event["at"].isoformat()})


def _timeline(
    started_at: datetime,
    started: dict[str, datetime],
    finished: dict[str, datetime],
    completed_at: datetime,
) -> list[dict]:
    def entry(step: str, at: datetime) -> dict:
        return {"step": step, "time": at.strftime("%H:%M:%S")}

    return [
        entry("Request received", started_at),
        *(entry(TIMELINE_LABELS[agent], started[agent]) for agent in PARALLEL_AGENTS),
        entry("Parallel agents complete", max(finished[agent] for agent in PARALLEL_AGENTS)),
        entry(TIMELINE_LABELS["compliance"], started["compliance"]),
        entry("Final report generated", completed_at),
    ]


async def synthesise_report(
    task_id: str,
    kyc_request: dict,
    identity: dict,
    screening: dict,
    corporate: dict,
    transaction: dict,
    compliance: dict,
) -> dict:
    """Assemble the agents' results into the final risk report."""

    comp_result = compliance.get("result", {}) or {}
    screening_result = screening.get("result", {}) or {}

    logger.info(
        "compliance_received",
        extra={
            "compliance_keys": list(compliance.keys()),
            "comp_result_keys": list(comp_result.keys()),
            "has_risk_summary": "risk_summary" in comp_result,
        },
    )
    retrieval_queries = int(screening_result.get("retrieval_queries", 0)) + int(
        comp_result.get("retrieval_queries", 0)
    )
    agents = {
        "identity": identity,
        "screening": screening,
        "corporate": corporate,
        "transaction": transaction,
        "compliance": compliance,
    }
    explanation = comp_result.get("explanation", "")

    report = {
        "report_id": f"argus-rpt-{task_id}",
        "generated_at": datetime.now(UTC).isoformat(),
        "explanation": explanation,
        "explanation_source": comp_result.get("explanation_source", "fallback"),
        "entity": {
            "name": kyc_request.get("entity_name"),
            "type": kyc_request.get("entity_type"),
            "jurisdiction": kyc_request.get("jurisdiction"),
        },
        "risk_summary": comp_result.get("risk_summary", {}),
        "dimension_scores": comp_result.get("dimension_scores", {}),
        "key_findings": comp_result.get("key_findings", []),
        "regulatory_triggers": comp_result.get("regulatory_triggers", []),
        "recommended_actions": comp_result.get("recommended_actions", []),
        "audit_trace": {
            "task_id": task_id,
            "agents_invoked": list(AGENTS),
            "retrieval_queries": retrieval_queries,
            "data_backend": configured_backend(),
            "agent_sources": {name: result.get("source") for name, result in agents.items()},
            "fallbacks": {
                name: result["fallbacks"]
                for name, result in agents.items()
                if result.get("fallbacks")
            },
            "identity_status": identity.get("status"),
            "screening_status": screening.get("status"),
            "corporate_status": corporate.get("status"),
            "transaction_status": transaction.get("status"),
            "compliance_status": compliance.get("status"),
        },
    }
    return report
