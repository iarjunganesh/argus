"""The study's week 1 baseline: today's analyst explanation for the six demo scenarios (arm A).

Each scenario reaches the Compliance agent as the workflow passes it (the request and the four
recorded agent responses), so the prompt is the one production sends, built by the production
code (`analyst_request`) and sent by it (`request_explanation`). A run writes the records of the
study protocol, section 13, into a folder of its own:

- `manifest.json`: run ID, times, ARGUS and protocol commits, policy version, case hashes, arm,
  model configuration, prices and spend;
- `requests.jsonl`: every request, with its item key, input exposure and regulatory passages;
- `responses.jsonl`: every response, with its outcome, explanation source, usage, latency and
  each attempt's error and spend.

    uv run python -m argus.study.baseline --out <folder> [--repeats 5]
        [--prices <prices.json> --ledger <spend.jsonl>]

A run with a model needs the token prices and the study's spend ledger (`argus.study.spend`):
each attempt is reserved against the protocol's ceilings before it is sent, and the run stops
before one that would pass them. Without a configured model (`ARGUS_MODEL_PROVIDER=none`) every
item is the template, labelled `fallback`: a check of the command, not a model baseline, and
nothing is spent. No secret, endpoint or key is written.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
from contextlib import nullcontext
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
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
from argus.study.spend import Ledger, Prices, cost, upper_bound, usd
from argus.utils.demo_profiles import SYNTHETIC_DEMO_CASES, get_demo_profile

ARM = "A"
# The study phase whose own spending ceiling the baseline's attempts count against (section 8).
PHASE = "week 1"
REPEATS = 5
# Retries of the identical request after a transport or service error (protocol section 8).
RETRIES = 2
# The OpenAI client's own retries, turned off so that RETRIES is the whole retry budget.
CLIENT_RETRIES = 0
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


@dataclass(frozen=True)
class Meter:
    """Reserves each attempt's upper bound before it is sent, and settles it afterwards."""

    prices: Prices
    ledger: Ledger
    # The model's length settings, which bound an attempt's output.
    settings: dict

    def reserve(self, key: str, prompt: str) -> tuple[Decimal, str | None]:
        """The attempt's reservation, and the ceiling it would pass (None once reserved)."""
        bound = upper_bound(self.prices, prompt, self.settings)
        return bound, self.ledger.reserve(key, PHASE, bound)

    def settle(self, key: str, bound: Decimal, call: ExplanationCall) -> Decimal:
        """What the attempt counts against the ceilings: its cost, or its whole reservation
        when the reply does not report its usage (a failed call may still be billed)."""
        spent = cost(self.prices, call.usage)
        if spent is None:
            return bound
        self.ledger.settle(key, spent)
        return spent


@dataclass
class Attempts:
    calls: list[ExplanationCall] = field(default_factory=list)
    # What each call counts against the ceilings, when the run is metered.
    spent: list[Decimal] = field(default_factory=list)
    # The ceiling the next attempt would have passed, and its reservation, when the run stops.
    stop: dict | None = None


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


async def _attempts(
    analyst: AnalystRequest, retries: int, meter: Meter | None, key: str
) -> Attempts:
    done = Attempts()
    # The client's own retries are off, so this loop alone decides how often a request is sent.
    while not done.calls or (done.calls[-1].error_kind == "call" and len(done.calls) <= retries):
        attempt = f"{key}/{len(done.calls) + 1}"
        if meter is None:
            done.calls.append(await request_explanation(analyst, client_retries=CLIENT_RETRIES))
            continue
        bound, ceiling = meter.reserve(attempt, analyst.prompt)
        if ceiling is not None:
            done.stop = {"ceiling": ceiling, "reservation_usd": usd(bound)}
            break
        call = await request_explanation(analyst, client_retries=CLIENT_RETRIES)
        done.calls.append(call)
        done.spent.append(meter.settle(attempt, bound, call))
    return done


def _outcome(last: ExplanationCall) -> str:
    if last.source == "model":
        return "model"
    return "failed" if last.error_kind == "call" else "fallback"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _usd(amounts: dict[str, Decimal]) -> dict[str, str]:
    return {name: usd(amount) for name, amount in amounts.items()}


def _meter(model: dict, prices: Prices | None, ledger: Ledger | None) -> Meter | None:
    """The run's meter; None without a model, since nothing is sent and nothing spent."""
    if model["provider"] == "none":
        return None
    if prices is None or ledger is None:
        raise RuntimeError(
            "A run with a model needs the token prices and a spending ledger "
            "(protocol section 8): pass --prices and --ledger."
        )
    return Meter(prices, ledger, model["settings"])


def _spend_record(ledger: Ledger | None, before: dict, stopped: dict | None) -> dict | None:
    """The manifest's spend: the ceilings, the ledger's totals before and after, and any stop."""
    if ledger is None:
        return None
    return {
        "phase": PHASE,
        "ledger": ledger.path.name,
        "ceilings_usd": _usd(ledger.ceilings(PHASE)),
        "before_usd": before,
        "after_usd": _usd(ledger.totals(PHASE)),
        "stopped": stopped,
    }


def _request_record(item: dict, prepared: Prepared, last: ExplanationCall, exposure: list) -> dict:
    sent = last.request is not None
    unsent = {"messages": [{"role": "user", "content": prepared.analyst.prompt}]}
    return {
        "item": item,
        "sent": sent,
        "request": last.request if sent else unsent,
        "input_exposure": exposure,
        "regulatory_passages": prepared.triggers,
    }


def _response_record(item: dict, at: str, done: Attempts, metered: bool) -> dict:
    last = done.calls[-1]
    attempts = []
    for number, attempt in enumerate(done.calls):
        kept = asdict(attempt)
        record = {k: kept[k] for k in ("error_kind", "error", "latency_seconds")}
        if metered:
            record["spend_usd"] = usd(done.spent[number])
        attempts.append(record)
    return {
        "item": item,
        "at": at,
        "outcome": _outcome(last),
        "explanation_source": last.source,
        "text": last.text,
        "response_model": last.response_model,
        "response_id": last.response_id,
        "usage": last.usage,
        "latency_seconds": last.latency_seconds,
        "attempts": attempts,
    }


async def run_baseline(
    out_dir: Path,
    repeats: int = REPEATS,
    retries: int = RETRIES,
    cases: list[Case] | None = None,
    run_id: str | None = None,
    prices: Prices | None = None,
    ledger: Ledger | None = None,
) -> Path:
    """Run arm A on the cases and write the run's records; returns the run's folder.

    A run with a model needs `prices` and `ledger`, and stops before an attempt that would pass
    a spending ceiling; the manifest's `spend.stopped` then says where.
    """
    if configured_backend() != "local":
        raise RuntimeError("The study runs on the local data plane: set ARGUS_DATA_BACKEND=local.")
    model = _model_configuration()
    meter = _meter(model, prices, ledger)
    cases = demo_cases() if cases is None else cases
    run_id = run_id or f"baseline-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:6]}"
    # The run holds the ledger throughout, and reads it afresh first: another run may have spent
    # since it was opened, and none may spend alongside it.
    with ledger.held(run_id) if ledger else nullcontext():
        return await _write_run(
            out_dir, run_id, repeats, retries, cases, model, prices, ledger, meter
        )


async def _write_run(
    out_dir: Path,
    run_id: str,
    repeats: int,
    retries: int,
    cases: list[Case],
    model: dict,
    prices: Prices | None,
    ledger: Ledger | None,
    meter: Meter | None,
) -> Path:
    started_at = _now()
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    listed = [{"case_id": c.case_id, **c.request, "hash": case_hash(c)} for c in cases]
    set_hash = hashlib.sha256(_canonical([c["hash"] for c in listed]).encode("utf-8")).hexdigest()
    before = _usd(ledger.totals(PHASE)) if ledger else {}
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
        "client_retries": CLIENT_RETRIES,
        "model": model,
        "prices": prices.record() if prices else None,
    }
    counts = {"items": 0, "model": 0, "fallback": 0, "failed": 0}
    stopped: dict | None = None
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
                key = f"{run_id}/{case.case_id}/{ARM}/{repeat}"
                done = await _attempts(prepared.analyst, retries, meter, key)
                if done.stop is not None:
                    stopped = {"before": {**item, "attempt": len(done.calls) + 1}, **done.stop}
                if done.calls:
                    record = _request_record(item, prepared, done.calls[-1], exposure)
                    requests.write(_canonical(record) + "\n")
                    response = _response_record(item, at, done, metered=meter is not None)
                    responses.write(_canonical(response) + "\n")
                    counts["items"] += 1
                    counts[response["outcome"]] += 1
                if stopped is not None:
                    break
            if stopped is not None:
                break

    manifest["ended_at"] = _now()
    manifest["counts"] = counts
    manifest["spend"] = _spend_record(ledger, before, stopped)
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return run_dir


def inside_working_directory(given: str) -> Path:
    """The file a command-line path names, refused unless it lies inside the working directory.

    The command may be run by an agent with arguments it chose, so it reads only files from the
    folder it runs in (usually the repository), never from elsewhere on the machine.
    """
    base = Path.cwd().resolve()
    path = (base / given).resolve()  # follows links and "..", so neither can lead outside
    if not path.is_relative_to(base):
        raise ValueError(f"{given} must be inside the working directory, {base}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m argus.study.baseline",
        description="Write the week 1 baseline: arm A on the six demo scenarios.",
    )
    parser.add_argument("--out", type=Path, required=True, help="folder to write the run into")
    parser.add_argument("--repeats", type=int, default=REPEATS, help="repeats per scenario")
    parser.add_argument(
        "--prices",
        help="token prices per million, with source and check date (JSON), in this folder",
    )
    parser.add_argument(
        "--ledger",
        help="the study's spend ledger, one file for all runs (JSON lines), in this folder",
    )
    args = parser.parse_args(argv)
    try:
        prices = Prices.load(inside_working_directory(args.prices)) if args.prices else None
        ledger = Ledger(inside_working_directory(args.ledger)) if args.ledger else None
        run_dir = asyncio.run(
            run_baseline(args.out, repeats=args.repeats, prices=prices, ledger=ledger)
        )
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    spend = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))["spend"]
    stopped = spend["stopped"] if spend else None
    if stopped:
        before = stopped["before"]
        print(
            f"Stopped at the {stopped['ceiling']} ceiling before {before['case_id']}, repeat "
            f"{before['repeat']}, attempt {before['attempt']}; the run folder holds what ran.",
            file=sys.stderr,
        )
    print(run_dir)
    return 1 if stopped else 0


if __name__ == "__main__":
    sys.exit(main())
