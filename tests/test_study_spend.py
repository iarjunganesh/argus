"""The study's token-spend stop: prices, the upper bound of an attempt and the spend ledger."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from argus.study import spend

PRICES = {
    "currency": "USD",
    "input": 0.825,
    "cached_input": 0.0825,
    "output": 4.95,
    "source": "https://prices.azure.com/api/retail/prices?example",
    "checked": "2026-11-22",
}


def _prices_file(tmp_path: Path, **changes) -> Path:
    path = tmp_path / "prices.json"
    fields = {**PRICES, **changes}
    path.write_text(json.dumps({k: v for k, v in fields.items() if v is not None}), "utf-8")
    return path


def _prices() -> spend.Prices:
    return spend.Prices(
        "USD", Decimal("0.825"), Decimal("0.0825"), Decimal("4.95"), "source", "2026-11-22"
    )


def test_prices_are_read_exactly_with_their_source_and_check_date(tmp_path):
    prices = spend.Prices.load(_prices_file(tmp_path))

    assert prices.input == Decimal("0.825")  # not the float 0.82499999...
    assert prices.cached_input == Decimal("0.0825")
    assert prices.output == Decimal("4.95")
    assert prices.record() == {
        "currency": "USD",
        "per_million_tokens": {"input": "0.825", "cached_input": "0.0825", "output": "4.95"},
        "source": "https://prices.azure.com/api/retail/prices?example",
        "checked": "2026-11-22",
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "EUR"},
        {"source": None},
        {"source": " "},
        {"checked": None},
        {"checked": "22 November"},
        {"input": 0},
        {"output": -4.95},
        {"output": "4.95"},
        {"output": True},
        {"cached_input": -0.01},
    ],
)
def test_prices_that_cannot_bound_the_spend_are_refused(tmp_path, changes):
    with pytest.raises(ValueError):
        spend.Prices.load(_prices_file(tmp_path, **changes))


def test_cached_input_may_be_free(tmp_path):
    assert spend.Prices.load(_prices_file(tmp_path, cached_input=0)).cached_input == 0


def test_an_attempt_is_bounded_by_every_prompt_byte_and_its_whole_completion_allowance():
    # "héllo" is 6 bytes in UTF-8; the message adds 16 tokens of framing at most.
    reasoning = spend.upper_bound(_prices(), "héllo", {"max_completion_tokens": 4000})
    classic = spend.upper_bound(_prices(), "héllo", {"max_tokens": 250, "temperature": 0.2})

    # (6 + 16) input tokens at 0.825 and 4000 output tokens at 4.95, per million.
    assert reasoning == Decimal("0.01981815")
    assert classic == Decimal("0.00125565")  # 22 x 0.825 + 250 x 4.95, per million


def test_an_attempt_without_a_completion_limit_has_no_bound():
    with pytest.raises(ValueError, match="completion limit"):
        spend.upper_bound(_prices(), "hello", {"temperature": 0.2})


def test_a_reply_costs_its_cached_input_apart_from_the_rest():
    usage = {
        "prompt_tokens": 1000,
        "completion_tokens": 2000,
        "total_tokens": 3000,
        "prompt_tokens_details": {"cached_tokens": 400, "audio_tokens": 0},
        "completion_tokens_details": {"reasoning_tokens": 1500},
    }

    # 600 x 0.825 + 400 x 0.0825 + 2000 x 4.95, per million.
    assert spend.cost(_prices(), usage) == Decimal("0.010428")
    assert spend.cost(_prices(), {"prompt_tokens": 1000, "completion_tokens": 0}) == Decimal(
        "0.000825"
    )


@pytest.mark.parametrize(
    "usage",
    [None, {}, {"prompt_tokens": 900}, {"prompt_tokens": "900", "completion_tokens": 80}],
)
def test_a_reply_without_its_token_counts_has_no_known_cost(usage):
    assert spend.cost(_prices(), usage) is None


def test_a_settled_attempt_counts_its_cost_and_an_unsettled_one_its_reservation(tmp_path):
    ledger = spend.Ledger(tmp_path / "spend.jsonl")

    assert ledger.reserve("run/a/1", "week 1", Decimal("0.02")) is None
    ledger.settle("run/a/1", Decimal("0.005"))
    assert ledger.reserve("run/b/1", "week 1", Decimal("0.03")) is None
    assert ledger.reserve("run/c/1", "week 2", Decimal("0.5")) is None

    assert ledger.totals("week 1") == {"study": Decimal("0.535"), "week 1": Decimal("0.035")}
    assert ledger.totals("week 2") == {"study": Decimal("0.535"), "week 2": Decimal("0.5")}


def test_the_ledger_carries_its_totals_across_restarts(tmp_path):
    path = tmp_path / "spend.jsonl"
    first = spend.Ledger(path)
    first.reserve("run-1/a/1", "week 1", Decimal("0.02"))
    first.settle("run-1/a/1", Decimal("0.004"))
    first.reserve("run-1/a/2", "week 1", Decimal("0.02"))  # never settled: the process died

    again = spend.Ledger(path)

    assert again.totals("week 1") == {"study": Decimal("0.024"), "week 1": Decimal("0.024")}


def test_a_reservation_may_reach_a_ceiling_but_not_pass_it(tmp_path):
    path = tmp_path / "spend.jsonl"
    ledger = spend.Ledger(path)
    ledger.reserve("earlier", "week 1", Decimal("1.98"))

    assert ledger.reserve("fits", "week 1", Decimal("0.02")) is None
    written = path.read_text("utf-8")
    assert ledger.reserve("passes", "week 1", Decimal("0.000001")) == "week 1"
    assert path.read_text("utf-8") == written  # a refused reservation is not recorded
    assert ledger.totals("week 1")["week 1"] == Decimal("2.00")


def test_the_study_ceiling_holds_across_phases(tmp_path):
    ledger = spend.Ledger(tmp_path / "spend.jsonl")
    ledger.reserve("weeks 2 to 5", "week 2", Decimal("19.99"))

    assert ledger.reserve("week 1 item", "week 1", Decimal("0.02")) == "study"
    assert ledger.reserve("week 1 item", "week 1", Decimal("0.01")) is None


def test_the_ceilings_are_the_protocols(tmp_path):
    assert spend.Ledger(tmp_path / "spend.jsonl").ceilings("week 1") == {
        "study": Decimal("20"),
        "week 1": Decimal("2"),
    }
    assert spend.Ledger(tmp_path / "spend.jsonl").ceilings("week 2") == {"study": Decimal("20")}


@pytest.mark.parametrize(
    "line",
    [
        "not json",
        '{"key": "a", "event": "refunded", "usd": "1"}',
        '{"key": "a", "event": "reserved", "usd": "1"}',  # no phase
        '{"key": "a", "event": "reserved", "phase": null, "usd": "1"}',
        '{"key": 7, "event": "reserved", "phase": "week 1", "usd": "1"}',
        '{"key": "a", "event": "reserved", "phase": "week 1", "usd": "lots"}',
        '{"key": "a", "event": "reserved", "phase": "week 1", "usd": "-1"}',
        '{"key": "unknown", "event": "settled", "usd": "1"}',
        "[]",
    ],
)
def test_a_damaged_ledger_is_refused(tmp_path, line):
    path = tmp_path / "spend.jsonl"
    path.write_text(line + "\n", "utf-8")

    with pytest.raises(ValueError, match="line 1"):
        spend.Ledger(path)


def test_every_entry_is_on_disk_when_the_call_returns(tmp_path):
    path = tmp_path / "spend.jsonl"
    ledger = spend.Ledger(path)
    ledger.reserve("run/a/1", "week 1", Decimal("0.0198"))
    ledger.settle("run/a/1", Decimal("0.00000123"))

    entries = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
    assert [(e["key"], e["event"], e.get("phase"), e["usd"]) for e in entries] == [
        ("run/a/1", "reserved", "week 1", "0.0198"),
        ("run/a/1", "settled", None, "0.00000123"),  # never in exponent form
    ]
    assert all(e["at"] for e in entries)
