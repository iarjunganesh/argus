"""The study's week 1 baseline: today's analyst explanation for the six demo scenarios (arm A)."""

import json
import re
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import argus.agents.compliance.tools.explain_decision as ed
import argus.agents.orchestrator.agent as orchestrator
from argus.findings import collect_findings
from argus.study import baseline, spend
from argus.utils.demo_profiles import SYNTHETIC_DEMO_CASES, get_demo_profile
from tests.test_compliance import FakeLLM


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _run(run_dir: Path) -> tuple[dict, list[dict], list[dict]]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    return manifest, _lines(run_dir / "requests.jsonl"), _lines(run_dir / "responses.jsonl")


PRICES = spend.Prices(
    "USD", Decimal("0.825"), Decimal("0.0825"), Decimal("4.95"), "retail prices", "2026-11-22"
)
# The length settings of a model that is not a reasoning model (`FakeLLM.model()`).
CLASSIC = {"max_tokens": 250, "temperature": 0.2}
# 700 input tokens at 0.825 and 80 output tokens at 4.95, per million.
USAGE = SimpleNamespace(prompt_tokens=700, completion_tokens=80)
USAGE_COST = Decimal("0.0009735")


@pytest.fixture
def budget(tmp_path) -> dict:
    """Prices and an empty study ledger, as `run_baseline` takes them."""
    return {"prices": PRICES, "ledger": spend.Ledger(tmp_path / "spend.jsonl")}


async def _bound(case: baseline.Case) -> Decimal:
    """One attempt's reservation for the case (test_study_spend checks the arithmetic)."""
    return spend.upper_bound(PRICES, (await baseline.prepare(case)).analyst.prompt, CLASSIC)


def test_the_cases_are_the_six_demo_scenarios_as_the_workflow_gives_them():
    cases = baseline.demo_cases()

    assert [c.case_id for c in cases] == [f"demo-{i}" for i in range(1, 7)]
    assert [tuple(c.request.values()) for c in cases] == list(SYNTHETIC_DEMO_CASES)
    for case in cases:
        profile = get_demo_profile(*case.request.values())
        upstream = case.payload["upstream_results"]
        assert list(upstream) == list(orchestrator.PARALLEL_AGENTS)
        for agent, response in upstream.items():
            assert response["source"] == "demo_profile"
            assert response["result"] == profile.get(agent, {})
    assert len({baseline.case_hash(c) for c in cases}) == 6


async def test_the_baseline_prompt_is_the_one_the_workflow_sends(monkeypatch):
    llm = FakeLLM(content="Explained.")
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    for case in baseline.demo_cases():
        await orchestrator.run_kyc_assessment(case.request)
        prepared = await baseline.prepare(case)
        assert prepared.analyst.prompt == llm.prompts[-1], case.case_id


def test_input_exposure_matches_exactly_and_after_normalising():
    prompt = "Entity: Cayman Synth Capital\nKey findings:\n- PEP   identified: minister"

    exposure = baseline.input_exposure(
        prompt,
        {"entity_name": ["Cayman Synth Capital"], "findings": ["pep identified: Minister", "Gone"]},
    )

    assert exposure == [
        {"kind": "entity_name", "text": "Cayman Synth Capital", "exact": True, "normalised": True},
        {
            "kind": "findings",
            "text": "pep identified: Minister",
            "exact": False,
            "normalised": True,
        },
        {"kind": "findings", "text": "Gone", "exact": False, "normalised": False},
    ]


async def test_the_case_strings_are_the_name_the_matched_names_and_the_findings():
    holdings = baseline.demo_cases()[0]  # a PEP match and adverse media

    prepared = await baseline.prepare(holdings)
    strings = baseline.case_strings(holdings.request["entity_name"], prepared.findings)

    hits = get_demo_profile(*holdings.request.values())["screening"]["findings"]
    summaries = [f.summary for f in prepared.findings.findings if f.summary]
    assert strings["entity_name"] == ["Synthetic Holdings B.V."]
    assert strings["matched_names"] == [hit["match"] for hit in hits]
    assert strings["findings"] == list(dict.fromkeys(summaries))


def test_a_match_reported_without_its_text_names_no_one():
    screening = {"source": "computed", "result": {"pep_hit": True, "findings": []}}

    strings = baseline.case_strings("Acme", collect_findings({"screening": screening}))

    assert strings["matched_names"] == []
    assert "PEP identified: " in strings["findings"]


async def test_a_run_without_a_model_records_every_item_as_a_fallback(tmp_path):
    run_dir = await baseline.run_baseline(tmp_path, repeats=2)

    manifest, requests, responses = _run(run_dir)
    assert run_dir.parent == tmp_path and run_dir.name == manifest["run_id"]
    assert manifest["arm"] == "A" and manifest["kind"] == "week 1 baseline"
    assert (manifest["repeats"], manifest["retries"], manifest["client_retries"]) == (2, 2, 0)
    assert manifest["model"] == {"provider": "none"}
    assert manifest["data_backend"] == "local"
    assert manifest["policy_version"] == "argus-risk-v1"
    assert manifest["prices"] is None and manifest["spend"] is None
    assert len(manifest["case_set"]["cases"]) == 6
    assert re.fullmatch(r"[0-9a-f]{64}", manifest["case_set"]["hash"])
    assert manifest["counts"] == {"items": 12, "model": 0, "fallback": 12, "failed": 0}
    assert manifest["started_at"] <= manifest["ended_at"]

    keys = [(r["item"]["case_id"], r["item"]["arm"], r["item"]["repeat"]) for r in requests]
    assert len(set(keys)) == 12 and keys[:2] == [("demo-1", "A", 1), ("demo-1", "A", 2)]
    first = requests[0]
    assert first["sent"] is False
    assert first["request"]["messages"][0]["content"].startswith("You are a senior KYC")
    assert {"kind": "entity_name", "text": "Synthetic Holdings B.V.", "exact": True,
            "normalised": True} in first["input_exposure"]  # fmt: skip
    assert first["regulatory_passages"]
    assert all(r["item"] == q["item"] for r, q in zip(responses, requests, strict=True))
    assert {r["outcome"] for r in responses} == {"fallback"}
    assert {r["explanation_source"] for r in responses} == {"fallback"}
    assert all(len(r["attempts"]) == 1 for r in responses)
    assert responses[0]["attempts"][0]["error_kind"] == "unavailable"


async def test_a_run_with_a_model_records_the_request_response_and_settings(
    monkeypatch, tmp_path, budget
):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "secret-key-value")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://secret-endpoint.example")
    llm = FakeLLM(content="Explained.", response={"model": "test-model-1", "usage": USAGE})
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    run_dir = await baseline.run_baseline(
        tmp_path, repeats=1, cases=baseline.demo_cases()[:2], **budget
    )

    manifest, requests, responses = _run(run_dir)
    assert manifest["model"] == {
        "provider": "test",
        "model": "test-model",
        "reasoning": False,
        "settings": {"max_tokens": 250, "temperature": 0.2},
    }
    assert manifest["counts"] == {"items": 2, "model": 2, "fallback": 0, "failed": 0}
    assert [r["request"] for r in requests] == llm.calls
    assert all(r["sent"] for r in requests)
    assert responses[0]["outcome"] == "model"
    assert responses[0]["text"] == "Explained."
    assert responses[0]["response_model"] == "test-model-1"
    assert responses[0]["usage"] == {"prompt_tokens": 700, "completion_tokens": 80}
    written = "".join(p.read_text(encoding="utf-8") for p in run_dir.iterdir())
    assert "secret-key-value" not in written and "secret-endpoint" not in written


async def test_a_failed_request_is_retried_up_to_twice(monkeypatch, tmp_path, budget):
    flaky = FakeLLM(content="Explained.", error=TimeoutError("timed out"), failures=2)
    monkeypatch.setattr(ed, "get_chat_model", flaky.model())

    run_dir = await baseline.run_baseline(
        tmp_path, repeats=1, cases=baseline.demo_cases()[:1], **budget
    )

    _, _, responses = _run(run_dir)
    assert responses[0]["outcome"] == "model"
    assert [a["error_kind"] for a in responses[0]["attempts"]] == ["call", "call", None]
    assert len({json.dumps(c, sort_keys=True) for c in flaky.calls}) == 1  # identical requests
    # The client's own retries are off, so every request sent is a recorded attempt.
    assert flaky.options == [{"max_retries": 0}] * 3


async def test_a_request_that_fails_after_its_retries_is_a_failure(monkeypatch, tmp_path, budget):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(error=TimeoutError("timed out")).model())

    run_dir = await baseline.run_baseline(
        tmp_path, repeats=1, cases=baseline.demo_cases()[:1], **budget
    )

    manifest, _, responses = _run(run_dir)
    assert responses[0]["outcome"] == "failed"
    assert responses[0]["explanation_source"] == "fallback"
    assert len(responses[0]["attempts"]) == 3
    assert responses[0]["attempts"][-1]["error"] == "TimeoutError: timed out"
    assert manifest["counts"] == {"items": 1, "model": 0, "fallback": 0, "failed": 1}


async def test_an_empty_reply_is_a_fallback_and_is_not_retried(monkeypatch, tmp_path, budget):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(content="").model())

    run_dir = await baseline.run_baseline(
        tmp_path, repeats=1, cases=baseline.demo_cases()[:1], **budget
    )

    _, _, responses = _run(run_dir)
    assert responses[0]["outcome"] == "fallback"
    assert [a["error_kind"] for a in responses[0]["attempts"]] == ["empty"]


async def test_a_run_needs_the_local_data_plane(monkeypatch, tmp_path):
    monkeypatch.setattr(baseline, "configured_backend", lambda: "azure")

    with pytest.raises(RuntimeError, match="local data plane"):
        await baseline.run_baseline(tmp_path, repeats=1)
    assert not any(tmp_path.iterdir())


async def test_an_existing_run_is_never_overwritten(tmp_path):
    (tmp_path / "baseline-taken").mkdir()

    with pytest.raises(FileExistsError):
        await baseline.run_baseline(tmp_path, repeats=1, run_id="baseline-taken")


def test_git_details_are_read_where_git_answers(monkeypatch, tmp_path):
    assert re.fullmatch(r"[0-9a-f]{40}", baseline.git("rev-parse", "HEAD") or "")
    # Stop Git from discovering the checkout when pytest's --basetemp is inside it.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert baseline.git("rev-parse", "HEAD", cwd=tmp_path) is None

    def missing(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", missing)
    assert baseline.git("rev-parse", "HEAD") is None
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert baseline.git("rev-parse", "HEAD") is None


def test_the_command_writes_a_run_and_prints_its_folder(tmp_path, capsys):
    assert baseline.main(["--out", str(tmp_path), "--repeats", "1"]) == 0

    run_dir = Path(capsys.readouterr().out.strip())
    assert run_dir.parent == tmp_path
    assert (run_dir / "manifest.json").exists()


# ── the spending stop (protocol section 8) ───────────────────────────────────


async def test_a_run_with_a_model_needs_prices_and_a_ledger(monkeypatch, tmp_path, budget):
    llm = FakeLLM(content="Explained.")
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    for missing in ({}, {"prices": PRICES}, {"ledger": budget["ledger"]}):
        with pytest.raises(RuntimeError, match="prices and a spending ledger"):
            await baseline.run_baseline(tmp_path, repeats=1, **missing)
    assert not any(tmp_path.iterdir()) and llm.calls == []


async def test_a_run_without_a_model_spends_nothing_from_the_ledger(tmp_path, budget):
    run_dir = await baseline.run_baseline(
        tmp_path, repeats=1, cases=baseline.demo_cases()[:1], **budget
    )

    manifest, _, responses = _run(run_dir)
    assert not (tmp_path / "spend.jsonl").exists()
    assert manifest["spend"]["after_usd"] == {"study": "0", "week 1": "0"}
    assert manifest["spend"]["stopped"] is None
    assert "spend_usd" not in responses[0]["attempts"][0]


async def test_each_attempt_is_reserved_then_settled_at_what_its_usage_cost(
    monkeypatch, tmp_path, budget
):
    llm = FakeLLM(content="Explained.", response={"usage": USAGE})
    monkeypatch.setattr(ed, "get_chat_model", llm.model())
    cases = baseline.demo_cases()[:2]

    run_dir = await baseline.run_baseline(tmp_path, repeats=1, cases=cases, **budget)

    manifest, _, responses = _run(run_dir)
    assert manifest["prices"] == {
        "currency": "USD",
        "per_million_tokens": {"input": "0.825", "cached_input": "0.0825", "output": "4.95"},
        "source": "retail prices",
        "checked": "2026-11-22",
    }
    ledger = _lines(tmp_path / "spend.jsonl")
    run_id = manifest["run_id"]
    assert [(e["key"], e["event"]) for e in ledger] == [
        (f"{run_id}/demo-1/A/1/1", "reserved"),
        (f"{run_id}/demo-1/A/1/1", "settled"),
        (f"{run_id}/demo-2/A/1/1", "reserved"),
        (f"{run_id}/demo-2/A/1/1", "settled"),
    ]
    assert [Decimal(e["usd"]) for e in ledger[::2]] == [await _bound(c) for c in cases]
    assert [Decimal(e["usd"]) for e in ledger[1::2]] == [USAGE_COST, USAGE_COST]
    assert [Decimal(r["attempts"][0]["spend_usd"]) for r in responses] == [USAGE_COST] * 2
    assert manifest["spend"] == {
        "phase": "week 1",
        "ledger": "spend.jsonl",
        "ceilings_usd": {"study": "20", "week 1": "2"},
        "before_usd": {"study": "0", "week 1": "0"},
        "after_usd": manifest["spend"]["after_usd"],
        "stopped": None,
    }
    assert {k: Decimal(v) for k, v in manifest["spend"]["after_usd"].items()} == {
        "study": 2 * USAGE_COST,
        "week 1": 2 * USAGE_COST,
    }


async def test_a_failed_attempt_keeps_its_whole_reservation(monkeypatch, tmp_path, budget):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(error=TimeoutError("timed out")).model())
    case = baseline.demo_cases()[0]

    run_dir = await baseline.run_baseline(tmp_path, repeats=1, cases=[case], **budget)

    manifest, _, responses = _run(run_dir)
    bound = await _bound(case)
    assert [e["event"] for e in _lines(tmp_path / "spend.jsonl")] == ["reserved"] * 3
    assert [Decimal(a["spend_usd"]) for a in responses[0]["attempts"]] == [bound] * 3
    assert Decimal(manifest["spend"]["after_usd"]["week 1"]) == 3 * bound


async def test_a_reply_without_usage_keeps_its_whole_reservation(monkeypatch, tmp_path, budget):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(content="Explained.").model())
    case = baseline.demo_cases()[0]

    run_dir = await baseline.run_baseline(tmp_path, repeats=1, cases=[case], **budget)

    _, _, responses = _run(run_dir)
    assert responses[0]["outcome"] == "model"
    assert [e["event"] for e in _lines(tmp_path / "spend.jsonl")] == ["reserved"]
    assert Decimal(responses[0]["attempts"][0]["spend_usd"]) == await _bound(case)


async def test_the_study_total_carries_over_from_earlier_runs(monkeypatch, tmp_path, budget):
    budget["ledger"].reserve("an earlier run", "week 1", Decimal("0.5"))
    budget["ledger"].reserve("week 2", "week 2", Decimal("3"))
    llm = FakeLLM(content="Explained.", response={"usage": USAGE})
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    run_dir = await baseline.run_baseline(
        tmp_path, repeats=1, cases=baseline.demo_cases()[:1], **budget
    )

    manifest, _, _ = _run(run_dir)
    assert manifest["spend"]["before_usd"] == {"study": "3.5", "week 1": "0.5"}
    assert {k: Decimal(v) for k, v in manifest["spend"]["after_usd"].items()} == {
        "study": Decimal("3.5") + USAGE_COST,
        "week 1": Decimal("0.5") + USAGE_COST,
    }


async def test_a_run_stops_before_an_attempt_that_would_pass_a_ceiling(
    monkeypatch, tmp_path, budget
):
    llm = FakeLLM(content="Explained.", response={"usage": USAGE})
    monkeypatch.setattr(ed, "get_chat_model", llm.model())
    case = baseline.demo_cases()[0]
    bound = await _bound(case)
    # Room for exactly one reservation: after it settles, a second would pass US$2 by its cost.
    budget["ledger"].reserve("earlier", "week 1", Decimal(2) - bound)

    run_dir = await baseline.run_baseline(tmp_path, repeats=3, cases=[case], **budget)

    manifest, requests, responses = _run(run_dir)
    assert len(llm.calls) == 1
    assert len(requests) == len(responses) == 1
    assert manifest["counts"] == {"items": 1, "model": 1, "fallback": 0, "failed": 0}
    assert manifest["spend"]["stopped"] == {
        "before": {"case_id": "demo-1", "arm": "A", "repeat": 2, "attempt": 1},
        "ceiling": "week 1",
        "reservation_usd": spend.usd(bound),
    }
    assert "ended_at" in manifest


async def test_a_stop_between_retries_records_the_attempts_made(monkeypatch, tmp_path, budget):
    llm = FakeLLM(error=TimeoutError("timed out"))
    monkeypatch.setattr(ed, "get_chat_model", llm.model())
    case = baseline.demo_cases()[0]
    budget["ledger"].reserve("earlier", "week 1", Decimal(2) - 2 * await _bound(case))

    run_dir = await baseline.run_baseline(tmp_path, repeats=1, cases=[case], **budget)

    manifest, requests, responses = _run(run_dir)
    assert len(llm.calls) == 2 and len(requests) == 1
    assert responses[0]["outcome"] == "failed"
    assert len(responses[0]["attempts"]) == 2
    assert manifest["counts"] == {"items": 1, "model": 0, "fallback": 0, "failed": 1}
    assert manifest["spend"]["stopped"]["before"] == {
        "case_id": "demo-1",
        "arm": "A",
        "repeat": 1,
        "attempt": 3,
    }


def _prices_file(tmp_path: Path) -> Path:
    path = tmp_path / "prices.json"
    path.write_text(
        '{"currency": "USD", "input": 0.825, "cached_input": 0.0825, "output": 4.95,'
        ' "source": "retail prices", "checked": "2026-11-22"}',
        "utf-8",
    )
    return path


def test_the_command_reads_the_prices_and_the_ledger(monkeypatch, tmp_path, capsys):
    llm = FakeLLM(content="Explained.", response={"usage": USAGE})
    monkeypatch.setattr(ed, "get_chat_model", llm.model())
    monkeypatch.chdir(tmp_path)
    _prices_file(tmp_path)

    args = ["--out", "runs", "--repeats", "1", "--prices", "prices.json", "--ledger", "spend.jsonl"]
    assert baseline.main(args) == 0

    run_dir = Path(capsys.readouterr().out.strip().splitlines()[-1])
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["prices"]["checked"] == "2026-11-22"
    assert len(_lines(tmp_path / "spend.jsonl")) == 12  # six scenarios, each reserved and settled


@pytest.mark.parametrize("outside", ["prices", "ledger"])
def test_the_command_reads_no_file_outside_the_working_directory(
    monkeypatch, tmp_path, capsys, outside
):
    llm = FakeLLM(content="Explained.", response={"usage": USAGE})
    monkeypatch.setattr(ed, "get_chat_model", llm.model())
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    files = {"prices": _prices_file(work), "ledger": work / "spend.jsonl"}
    files[outside] = tmp_path / files[outside].name  # beside the working directory, not in it
    if outside == "prices":
        _prices_file(tmp_path)

    args = ["--out", "runs", "--prices", str(files["prices"]), "--ledger", str(files["ledger"])]
    assert baseline.main(args) == 2

    assert "inside the working directory" in capsys.readouterr().err
    assert not (work / "runs").exists() and llm.calls == []


def test_the_command_reports_a_stop(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(content="Explained.").model())
    monkeypatch.chdir(tmp_path)
    ledger = tmp_path / "spend.jsonl"
    spend.Ledger(ledger).reserve("earlier", "week 1", Decimal(2))
    args = ["--out", str(tmp_path / "runs"), "--prices", str(_prices_file(tmp_path))]

    assert baseline.main([*args, "--ledger", str(ledger)]) == 1

    captured = capsys.readouterr()
    run_dir = Path(captured.out.strip().splitlines()[-1])
    assert (run_dir / "manifest.json").exists()
    assert "week 1 ceiling" in captured.err and "demo-1" in captured.err


def test_the_command_refuses_a_model_run_without_its_budget(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(content="Explained.").model())

    assert baseline.main(["--out", str(tmp_path / "runs")]) == 2

    captured = capsys.readouterr()
    assert captured.out == "" and "prices and a spending ledger" in captured.err
