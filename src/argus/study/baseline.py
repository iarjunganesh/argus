"""The study's week 1 baseline: today's analyst explanation for the six demo scenarios (arm A).

Each scenario reaches the Compliance agent as the workflow passes it (the request and the four
recorded agent responses), so the prompt is the one production sends, built by the production
code (`analyst_request`) and sent by it (`request_explanation`). A run writes the records of the
study protocol, section 13, into a folder of its own:

- `manifest.json`: run ID, times, ARGUS and protocol commits, policy version, case hashes, arm,
  model configuration and prices;
- `requests.jsonl`: every request, with its item key, input exposure and regulatory passages;
- `responses.jsonl`: every response, with its outcome, explanation source, usage, latency and
  each attempt's error.

    uv run python -m argus.study.baseline --out <folder> [--repeats 5]

Without a configured model (`ARGUS_MODEL_PROVIDER=none`) every item is the template, labelled
`fallback`: a check of the command, not a model baseline. No secret, endpoint or key is written.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from argus.agents.compliance import agent as compliance
from argus.agents.compliance.tools import explain_decision
from argus.agents.compliance.tools.explain_decision import (
    MAX_TOKENS,
    TEMPERATURE,
    AnalystRequest,
    ExplanationCall,
    request_explanation,
)
from argus.agents.orchestrator.agent import PARALLEL_AGENTS, compliance_payload, demo_response
from argus.data_plane import configured_backend
from argus.findings import POLICY_VERSION, FindingSet
from argus.utils.demo_profiles import SYNTHETIC_DEMO_CASES, get_demo_profile

ARM = "A"
REPEATS = 5
# Retries of the identical request after a transport or service error (protocol section 8).
RETRIES = 2
PROTOCOL = "docs/research/study-protocol.md"
# src/argus/study/baseline.py -> the repository root is three levels up.
REPO_ROOT = Path(__file__).resolve().parents[3]
MATCH_KINDS = ("sanctions_match", "pep_match", "adverse_media_match")


@dataclass(frozen=True)
class Case:
    case_id: str
    request: dict
    # What the Compliance agent reads: the request and the four upstream responses.
    payload: dict


@dataclass(frozen=True)
class Prepared:
    analyst: AnalystRequest
    findings: FindingSet
    triggers: list[dict]


def demo_cases() -> list[Case]:
    """The six demo scenarios, in `SYNTHETIC_DEMO_CASES` order, as the workflow builds them."""
    cases = []
    for number, (name, kind, jurisdiction) in enumerate(SYNTHETIC_DEMO_CASES, start=1):
        case_id = f"demo-{number}"
        request = {"entity_name": name, "entity_type": kind, "jurisdiction": jurisdiction}
        profile = get_demo_profile(name, kind, jurisdiction) or {}
        responses = [demo_response(agent, case_id, profile) for agent in PARALLEL_AGENTS]
        cases.append(Case(case_id, request, compliance_payload(request, responses)))
    return cases


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def case_hash(case: Case) -> str:
    return hashlib.sha256(_canonical(case.payload).encode("utf-8")).hexdigest()


async def prepare(case: Case) -> Prepared:
    """The case's analyst request, through the Compliance agent's own preparation."""
    prepared = await compliance.prepare(case.payload, case.case_id)
    return Prepared(prepared.analyst_request(), prepared.records, prepared.triggers)


def normalise(text: str) -> str:
    return " ".join(text.casefold().split())


def case_strings(entity_name: str, findings: FindingSet) -> dict[str, list[str]]:
    """The case strings whose exposure the protocol measures (section 9.1)."""
    matched = []
    for finding in findings.findings:
        if finding.kind not in MATCH_KINDS:
            continue
        for ref in finding.evidence_refs:
            data = findings.evidence[ref].data
            match = data.get("match") if isinstance(data, dict) else None
            if isinstance(match, str) and match:
                matched.append(match)
    summaries = [f.summary for f in findings.findings if f.summary]
    return {
        "entity_name": [entity_name],
        "matched_names": list(dict.fromkeys(matched)),
        "findings": list(dict.fromkeys(summaries)),
    }


def input_exposure(prompt: str, strings: dict[str, list[str]]) -> list[dict]:
    """Which case strings appear in the prompt, exactly and after case-folding and spacing."""
    folded = normalise(prompt)
    return [
        {
            "kind": kind,
            "text": text,
            "exact": text in prompt,
            "normalised": normalise(text) in folded,
        }
        for kind, texts in strings.items()
        for text in texts
    ]


def git(*args: str, cwd: Path = REPO_ROOT) -> str | None:
    """A git answer, or None where git or the repository is not available."""
    executable = shutil.which("git")
    if executable is None:
        return None
    try:
        done = subprocess.run(  # noqa: S603 - fixed arguments, no shell
            [executable, *args], cwd=cwd, capture_output=True, text=True, check=True, timeout=30
        )
    except OSError, subprocess.SubprocessError:
        return None
    return done.stdout.strip()


def _model_configuration() -> dict:
    try:
        # The configuration the explanation itself uses.
        chat = explain_decision.get_chat_model()
    except Exception:  # noqa: BLE001 - no usable model: the run is the template, labelled
        return {"provider": "none"}
    return {
        "provider": chat.provider,
        "model": chat.model,
        "reasoning": chat.reasoning,
        "settings": chat.limits(max_tokens=MAX_TOKENS, temperature=TEMPERATURE),
    }


async def _attempts(analyst: AnalystRequest, retries: int) -> list[ExplanationCall]:
    attempts = [await request_explanation(analyst)]
    while attempts[-1].error_kind == "call" and len(attempts) <= retries:
        attempts.append(await request_explanation(analyst))
    return attempts


def _outcome(last: ExplanationCall) -> str:
    if last.source == "model":
        return "model"
    return "failed" if last.error_kind == "call" else "fallback"


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def run_baseline(
    out_dir: Path,
    repeats: int = REPEATS,
    retries: int = RETRIES,
    cases: list[Case] | None = None,
    run_id: str | None = None,
) -> Path:
    """Run arm A on the cases and write the run's records; returns the run's folder."""
    if configured_backend() != "local":
        raise RuntimeError("The study runs on the local data plane: set ARGUS_DATA_BACKEND=local.")
    cases = demo_cases() if cases is None else cases
    started_at = _now()
    run_id = run_id or f"baseline-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:6]}"
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    listed = [{"case_id": c.case_id, **c.request, "hash": case_hash(c)} for c in cases]
    set_hash = hashlib.sha256(_canonical([c["hash"] for c in listed]).encode("utf-8")).hexdigest()
    manifest: dict[str, object] = {
        "run_id": run_id,
        "kind": "week 1 baseline",
        "arm": ARM,
        "started_at": started_at,
        "argus_commit": git("rev-parse", "HEAD"),
        "argus_tree_changed": bool(git("status", "--porcelain", "--untracked-files=no")),
        "protocol_commit": git("log", "-1", "--format=%H", "--", PROTOCOL),
        "policy_version": POLICY_VERSION,
        "data_backend": "local",
        "case_set": {"hash": set_hash, "cases": listed},
        "repeats": repeats,
        "retries": retries,
        "model": _model_configuration(),
        # Recorded with their source when the budget is set (protocol section 8).
        "prices": None,
    }
    counts = {"items": 0, "model": 0, "fallback": 0, "failed": 0}
    with (
        (run_dir / "requests.jsonl").open("w", encoding="utf-8") as requests,
        (run_dir / "responses.jsonl").open("w", encoding="utf-8") as responses,
    ):
        for case in cases:
            prepared = await prepare(case)
            exposure = input_exposure(
                prepared.analyst.prompt,
                case_strings(case.request["entity_name"], prepared.findings),
            )
            for repeat in range(1, repeats + 1):
                item = {"case_id": case.case_id, "arm": ARM, "repeat": repeat}
                at = _now()
                attempts = await _attempts(prepared.analyst, retries)
                last = attempts[-1]
                sent = last.request is not None
                unsent = {"messages": [{"role": "user", "content": prepared.analyst.prompt}]}
                requests.write(
                    _canonical(
                        {
                            "item": item,
                            "sent": sent,
                            "request": last.request if sent else unsent,
                            "input_exposure": exposure,
                            "regulatory_passages": prepared.triggers,
                        }
                    )
                    + "\n"
                )
                outcome = _outcome(last)
                counts["items"] += 1
                counts[outcome] += 1
                responses.write(
                    _canonical(
                        {
                            "item": item,
                            "at": at,
                            "outcome": outcome,
                            "explanation_source": last.source,
                            "text": last.text,
                            "response_model": last.response_model,
                            "response_id": last.response_id,
                            "usage": last.usage,
                            "latency_seconds": last.latency_seconds,
                            "attempts": [
                                {
                                    key: value
                                    for key, value in asdict(attempt).items()
                                    if key in ("error_kind", "error", "latency_seconds")
                                }
                                for attempt in attempts
                            ],
                        }
                    )
                    + "\n"
                )

    manifest["ended_at"] = _now()
    manifest["counts"] = counts
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m argus.study.baseline",
        description="Write the week 1 baseline: arm A on the six demo scenarios.",
    )
    parser.add_argument("--out", type=Path, required=True, help="folder to write the run into")
    parser.add_argument("--repeats", type=int, default=REPEATS, help="repeats per scenario")
    args = parser.parse_args(argv)
    run_dir = asyncio.run(run_baseline(args.out, repeats=args.repeats))
    print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
