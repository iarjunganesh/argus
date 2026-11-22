"""The study's week 1 baseline: today's analyst explanation for the six demo scenarios (arm A)."""

import json
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import argus.agents.compliance.tools.explain_decision as ed
import argus.agents.orchestrator.agent as orchestrator
from argus.findings import collect_findings
from argus.study import baseline
from argus.utils.demo_profiles import SYNTHETIC_DEMO_CASES, get_demo_profile
from tests.test_compliance import FakeLLM


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _run(run_dir: Path) -> tuple[dict, list[dict], list[dict]]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    return manifest, _lines(run_dir / "requests.jsonl"), _lines(run_dir / "responses.jsonl")


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
    assert manifest["prices"] is None
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


async def test_a_run_with_a_model_records_the_request_response_and_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "secret-key-value")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://secret-endpoint.example")
    usage = SimpleNamespace(prompt_tokens=700, completion_tokens=80)
    llm = FakeLLM(content="Explained.", response={"model": "test-model-1", "usage": usage})
    monkeypatch.setattr(ed, "get_chat_model", llm.model())

    run_dir = await baseline.run_baseline(tmp_path, repeats=1, cases=baseline.demo_cases()[:2])

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


async def test_a_failed_request_is_retried_up_to_twice(monkeypatch, tmp_path):
    flaky = FakeLLM(content="Explained.", error=TimeoutError("timed out"), failures=2)
    monkeypatch.setattr(ed, "get_chat_model", flaky.model())

    run_dir = await baseline.run_baseline(tmp_path, repeats=1, cases=baseline.demo_cases()[:1])

    _, _, responses = _run(run_dir)
    assert responses[0]["outcome"] == "model"
    assert [a["error_kind"] for a in responses[0]["attempts"]] == ["call", "call", None]
    assert len({json.dumps(c, sort_keys=True) for c in flaky.calls}) == 1  # identical requests
    # The client's own retries are off, so every request sent is a recorded attempt.
    assert flaky.options == [{"max_retries": 0}] * 3


async def test_a_request_that_fails_after_its_retries_is_a_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(error=TimeoutError("timed out")).model())

    run_dir = await baseline.run_baseline(tmp_path, repeats=1, cases=baseline.demo_cases()[:1])

    manifest, _, responses = _run(run_dir)
    assert responses[0]["outcome"] == "failed"
    assert responses[0]["explanation_source"] == "fallback"
    assert len(responses[0]["attempts"]) == 3
    assert responses[0]["attempts"][-1]["error"] == "TimeoutError: timed out"
    assert manifest["counts"] == {"items": 1, "model": 0, "fallback": 0, "failed": 1}


async def test_an_empty_reply_is_a_fallback_and_is_not_retried(monkeypatch, tmp_path):
    monkeypatch.setattr(ed, "get_chat_model", FakeLLM(content="").model())

    run_dir = await baseline.run_baseline(tmp_path, repeats=1, cases=baseline.demo_cases()[:1])

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
