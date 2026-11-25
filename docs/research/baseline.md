# The week 1 baseline command

Status: **command built on 2026-11-22, spending stop added on 2026-11-25; no model baseline has
been captured.** A model run waits for the frozen protocol
([`study-protocol.md`](study-protocol.md), section 16).

The command captures today's analyst explanation (arm A) for the six demo scenarios, five times
each, with the exact prompt, the model configuration and who wrote each output:

```sh
uv run python -m argus.study.baseline --out <folder> [--repeats 5]
    [--prices <prices.json> --ledger <spend.jsonl>]
```

The last line of standard output gives the run's folder,
`<folder>/baseline-<UTC time>-<suffix>/`. Each run gets its own folder. The command exits with
0 when the run finished, 1 when it stopped at a spending ceiling (the reason is on standard
error and in the manifest), and 2 when it refused to start.

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
that checks the command, is not a model baseline, and spends nothing.

## Prices and the spending stop

A run with a model refuses to start without `--prices` and `--ledger` (protocol section 8;
`src/argus/study/spend.py`).

- **Prices** are a JSON file in US dollars per million tokens, with where and when they were
  checked. Check them on the day of the run; the manifest records the file's values.

  ```json
  {"currency": "USD", "input": 0.825, "cached_input": 0.0825, "output": 4.95,
   "source": "<the retail price query and its meters>", "checked": "2026-11-22"}
  ```

  These are the Data Zone Standard rates for `gpt-5.4-mini` in Sweden Central checked on
  2026-11-22 and again on 2026-11-25 (the protocol's link, meters `5.4 mini Inp Dz`,
  `5.4 mini cd Inp Dz` and `5.4 mini Opt Dz`).
- **The ledger** is one file of JSON lines for the whole study, so its totals carry across runs
  and restarts. Use the same file for every run; a new file starts the study's total at zero.
  It is created on the first attempt.
- **Before each attempt**, retries included, the run reserves an upper bound on the attempt's
  cost: every prompt byte priced as an uncached input token (a token is at least one byte), 16
  tokens of message framing, and the whole completion allowance (`max_completion_tokens`, 4000
  for a reasoning model, reasoning included) priced as output. The reservation is written and
  flushed to disk before the request is sent.
- **After the attempt**, the reservation is settled at the cost the reply's usage reports
  (cached input at its own rate). A failed call, or a reply without usage, keeps its whole
  reservation, since it may still be billed.
- **The stop.** A reservation that would take the study's total past US$20, or week 1's past
  US$2, is not made: the run sends nothing more, writes what ran, and records the stop.

At the 2026-11-22 rates, each demo prompt's attempt reserves about US$0.021. Week 1's 30 items
reserve about US$0.64 in all, and even if all 90 possible attempts failed and kept their full
reservations, the run would count US$1.91 against week 1's US$2. A second full week 1 run would
not fit under that ceiling.

## What a run holds

The records of protocol section 13:

| File | What it holds |
| --- | --- |
| `manifest.json` | Run ID, start and end times, the ARGUS commit and whether tracked files had changed, the protocol's last commit, the policy version, each case's SHA-256 hash and the case set's, the arm, repeats, retries and the client's own retries (0), the model configuration (provider, model, whether it reasons, its length and sampling settings), the prices with their source and check date, the spend (the ceilings, the ledger's totals before and after the run, and where it stopped, if it did) and the outcome counts |
| `requests.jsonl` | Per item (case, arm, repeat): the exact request (model, messages, settings), whether it was sent, the input exposure and the regulatory passages retrieved |
| `responses.jsonl` | Per item: the outcome (`model`, `fallback` or `failed`), the explanation source, the text, the response's model and ID, the usage, the latency, and each attempt's error and, in a run with a model, what it counted against the ceilings |

Input exposure lists each case string (the entity name, the matched names in the screening
evidence, and the typed findings' summaries) with whether it appears in the prompt exactly and
after case-folding and collapsing spaces (section 9.1). No secret, endpoint or key is written.

A model output in arm A counts only when its outcome is `model`; `fallback` and `failed` items
are excluded and counted (section 11). A run that stopped at a ceiling reports its partial
results as such.
