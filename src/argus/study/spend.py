"""The study's token-spend stop (protocol section 8).

Before each attempt, including retries, the runner reserves an upper bound on the attempt's
token cost in a ledger kept on disk. After the attempt the reservation is settled at the cost
the reply's usage reports, or kept whole when the usage is unknown (a failed call may still be
billed). The ledger is one append-only file for the whole study, so its totals carry across runs
and restarts. A reservation that would take the study total past US$20, or a phase's total past
its own ceiling (US$2 for week 1), is refused and not recorded: the run stops before that
attempt and reports the stop.

Amounts are `Decimal`s, written in plain notation, so that sums are exact.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

CURRENCY = "USD"
STUDY_CEILING = Decimal(20)
PHASE_CEILINGS = {"week 1": Decimal(2)}
# A message's role and separators, and the reply's priming, take a few tokens beyond its content;
# 16 is more than the Chat Completions format uses.
FRAMING_TOKENS = 16
MILLION = Decimal(1_000_000)


def usd(amount: Decimal) -> str:
    """An amount in plain notation, never in exponent form."""
    return format(amount, "f")


def _price(fields: dict, name: str, minimum_exclusive: bool) -> Decimal:
    value = fields.get(name)
    # JSON numbers only (parsed as Decimal); bool is an int and a string is not a number.
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise ValueError(f"prices: {name} must be a number per million tokens")
    value = Decimal(value)
    if value < 0 or (minimum_exclusive and value == 0):
        raise ValueError(f"prices: {name} must be {'above' if minimum_exclusive else 'at least'} 0")
    return value


@dataclass(frozen=True)
class Prices:
    """Token prices per million, in US dollars, with where and when they were checked."""

    currency: str
    input: Decimal
    cached_input: Decimal
    output: Decimal
    source: str
    checked: str

    @classmethod
    def load(cls, path: Path) -> Prices:
        fields = json.loads(Path(path).read_text(encoding="utf-8"), parse_float=Decimal)
        if fields.get("currency") != CURRENCY:
            raise ValueError(f"prices: currency must be {CURRENCY}, as the ceilings are")
        source = fields.get("source")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("prices: source must say where the prices come from")
        try:
            checked = date.fromisoformat(str(fields.get("checked"))).isoformat()
        except ValueError:
            raise ValueError("prices: checked must be the date they were checked") from None
        return cls(
            CURRENCY,
            _price(fields, "input", minimum_exclusive=True),
            _price(fields, "cached_input", minimum_exclusive=False),
            _price(fields, "output", minimum_exclusive=True),
            source,
            checked,
        )

    def record(self) -> dict:
        return {
            "currency": self.currency,
            "per_million_tokens": {
                "input": usd(self.input),
                "cached_input": usd(self.cached_input),
                "output": usd(self.output),
            },
            "source": self.source,
            "checked": self.checked,
        }


def upper_bound(prices: Prices, prompt: str, settings: dict) -> Decimal:
    """A cost one attempt cannot pass: each prompt byte priced as an uncached input token (a
    token is at least one byte), plus framing, and the whole completion allowance as output
    (for a reasoning model it includes the reasoning)."""
    allowance = settings.get("max_completion_tokens", settings.get("max_tokens"))
    if not isinstance(allowance, int):
        raise ValueError("an attempt without a completion limit has no upper bound")
    input_tokens = len(prompt.encode("utf-8")) + FRAMING_TOKENS
    return (input_tokens * prices.input + allowance * prices.output) / MILLION


def cost(prices: Prices, usage: dict | None) -> Decimal | None:
    """What a reply's usage costs, or None when it does not report its token counts."""
    usage = usage or {}
    prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if not isinstance(prompt, int) or not isinstance(completion, int):
        return None
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    return (
        (prompt - cached) * prices.input + cached * prices.cached_input + completion * prices.output
    ) / MILLION


class Ledger:
    """The study's spend: one append-only file of reservations and settlements."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._phase: dict[str, str] = {}
        self._amount: dict[str, Decimal] = {}
        if self.path.exists():
            lines = self.path.read_text(encoding="utf-8").splitlines()
            for number, line in enumerate(lines, start=1):
                try:
                    self._apply(json.loads(line))
                except (ValueError, TypeError, KeyError, AttributeError, InvalidOperation) as exc:
                    raise ValueError(f"{self.path}: line {number} is not a ledger entry") from exc

    def _apply(self, entry: dict) -> None:
        key, event, amount = entry["key"], entry["event"], Decimal(entry["usd"])
        if not isinstance(key, str) or not amount.is_finite() or amount < 0:
            raise ValueError("an entry needs a key and an amount of at least 0")
        if event == "reserved":
            if not isinstance(entry["phase"], str):
                raise ValueError("a reservation needs its phase")
            self._phase[key] = entry["phase"]
        elif event != "settled" or key not in self._phase:
            raise ValueError(f"unknown entry {event!r} for {key!r}")
        self._amount[key] = amount

    def _write(self, entry: dict) -> None:
        entry = {"at": datetime.now(UTC).isoformat(), **entry}
        with self.path.open("a", encoding="utf-8") as ledger:
            ledger.write(json.dumps(entry, ensure_ascii=False) + "\n")
            ledger.flush()
            os.fsync(ledger.fileno())  # a reservation must survive a crash during its attempt
        self._apply(entry)

    @staticmethod
    def ceilings(phase: str) -> dict[str, Decimal]:
        """The ceilings a phase's attempts are held to: the study's and the phase's own."""
        own = {phase: PHASE_CEILINGS[phase]} if phase in PHASE_CEILINGS else {}
        return {"study": STUDY_CEILING, **own}

    def totals(self, phase: str) -> dict[str, Decimal]:
        """The study's total and the phase's, each attempt at its settled cost or reservation."""
        in_phase = (amount for key, amount in self._amount.items() if self._phase[key] == phase)
        return {"study": sum(self._amount.values(), Decimal(0)), phase: sum(in_phase, Decimal(0))}

    def reserve(self, key: str, phase: str, amount: Decimal) -> str | None:
        """Reserve an attempt's upper bound; returns the ceiling it would pass, recording
        nothing, or None once it is recorded."""
        totals = self.totals(phase)
        for name, ceiling in self.ceilings(phase).items():
            if totals[name] + amount > ceiling:
                return name
        self._write({"key": key, "event": "reserved", "phase": phase, "usd": usd(amount)})
        return None

    def settle(self, key: str, amount: Decimal) -> None:
        """Replace an attempt's reservation with what it cost."""
        self._write({"key": key, "event": "settled", "usd": usd(amount)})
