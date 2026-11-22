# The week 1 baseline command

Status: **command built on 2026-11-22; no model baseline has been captured.** A model run waits
for the frozen protocol and the budget ([`study-protocol.md`](study-protocol.md), sections 8 and
16).

The command captures today's analyst explanation (arm A) for the six demo scenarios, five times
each, with the exact prompt, the model configuration and who wrote each output:

```sh
uv run python -m argus.study.baseline --out <folder> [--repeats 5]
```

It prints the run's folder, `<folder>/baseline-<UTC time>-<suffix>/`, and never writes over an
existing run.

## What it runs

Each scenario reaches the Compliance agent as the workflow builds it: the request and the four
recorded agent responses (`demo_response` and `compliance_payload` in the orchestrator). The
Compliance agent's own preparation (`prepare`) evaluates the findings and retrieves the
regulations. The production code then writes the prompt (`analyst_request`) and sends it
(`request_explanation`), so the prompt is the one a live assessment sends; a test checks that
for all six scenarios. A request that fails is retried twice with the identical request
(protocol section 8). The OpenAI client's own retries (two by default) are turned off for these
calls, so every request sent is an attempt the run records. The run refuses any data plane but
the local one (section 2).

The model is the one `ARGUS_MODEL_PROVIDER` configures (`src/argus/models.py`). Without one
(`ARGUS_MODEL_PROVIDER=none`, the default), every output is the template, labelled `fallback`:
that checks the command and is not a model baseline.

## What a run holds

The records of protocol section 13:

| File | What it holds |
| --- | --- |
| `manifest.json` | Run ID, start and end times, the ARGUS commit and whether tracked files had changed, the protocol's last commit, the policy version, each case's SHA-256 hash and the case set's, the arm, repeats, retries and the client's own retries (0), the model configuration (provider, model, whether it reasons, its length and sampling settings), the prices (empty until the budget is set) and the outcome counts |
| `requests.jsonl` | Per item (case, arm, repeat): the exact request (model, messages, settings), whether it was sent, the input exposure and the regulatory passages retrieved |
| `responses.jsonl` | Per item: the outcome (`model`, `fallback` or `failed`), the explanation source, the text, the response's model and ID, the usage, the latency, and each attempt's error |

Input exposure lists each case string (the entity name, the matched names in the screening
evidence, and the typed findings' summaries) with whether it appears in the prompt exactly and
after case-folding and collapsing spaces (section 9.1). No secret, endpoint or key is written.

A model output in arm A counts only when its outcome is `model`; `fallback` and `failed` items
are excluded and counted (section 11).
