"""Canonical facts and retained evidence, independent of cached agent scores.

IDs are content-derived within a report, not identifiers assigned by a source. Repeated identical
facts get occurrence suffixes so counts survive; their set of IDs is stable under reordering.
Observation times and cached scores never participate in an ID. Nothing here confirms a match or
records a human decision. The evidence index is retained with the report and expires with it.
"""

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

POLICY_VERSION: Literal["argus-risk-v1"] = "argus-risk-v1"
type Category = Literal["identity", "screening", "corporate", "transaction"]
type FindingKind = Literal[
    "assessment",
    "discrepancy",
    "sanctions_match",
    "pep_match",
    "adverse_media_match",
    "corporate_flag",
    "ownership_depth",
    "structuring",
    "layering",
    "typology",
]
type AssessmentState = Literal["completed", "partial", "not_assessed", "skipped"]
CATEGORIES: tuple[Category, ...] = ("identity", "screening", "corporate", "transaction")
SCREENING_CHECKS: tuple[tuple[str, str, FindingKind], ...] = (
    ("sanctions", "sanctions_checker", "sanctions_match"),
    ("pep", "pep_checker", "pep_match"),
    ("adverse_media", "adverse_media_scanner", "adverse_media_match"),
)


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    source: str
    reference: dict[str, JsonValue]
    data: JsonValue
    source_at: str | None


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    category: Category
    kind: FindingKind
    scope: str
    value: str | int | bool
    summary: str
    evidence_refs: tuple[str, ...]
    source: str
    source_at: str | None
    observed_at: datetime
    uncertainty: Literal["observed", "potential", "unknown"]
    review_status: Literal["pending"] = "pending"
    policy_version: Literal["argus-risk-v1"] = POLICY_VERSION

    @model_validator(mode="after")
    def validate_fact(self) -> Finding:
        categories = {
            "discrepancy": "identity",
            "sanctions_match": "screening",
            "pep_match": "screening",
            "adverse_media_match": "screening",
            "corporate_flag": "corporate",
            "ownership_depth": "corporate",
            "structuring": "transaction",
            "layering": "transaction",
            "typology": "transaction",
        }
        if self.kind != "assessment" and self.category != categories[self.kind]:
            raise ValueError("Finding kind does not belong to its category")
        scopes = (
            ("sanctions", "pep", "adverse_media")
            if self.category == "screening"
            else (self.category,)
        )
        if self.scope not in scopes:
            raise ValueError("Finding scope does not belong to its category")
        if self.kind.endswith("_match") and self.scope != self.kind.removesuffix("_match"):
            raise ValueError("Screening finding scope does not match its kind")
        if self.kind == "assessment":
            valid = self.value in ("completed", "partial", "not_assessed", "skipped")
        elif self.kind == "discrepancy":
            valid = self.value in ("high", "medium", "low", "unknown")
        elif self.kind == "ownership_depth":
            valid = type(self.value) is int and self.value > 3
        else:
            valid = self.value is True
        if not valid:
            raise ValueError("Invalid value for this finding kind")
        return self


class FindingSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    findings: tuple[Finding, ...]
    evidence: dict[str, EvidenceRecord]

    @model_validator(mode="after")
    def validate_references(self) -> FindingSet:
        if any(key != record.id for key, record in self.evidence.items()):
            raise ValueError("The evidence index does not match its record identifiers")
        for finding in self.findings:
            if not finding.evidence_refs or any(
                ref not in self.evidence for ref in finding.evidence_refs
            ):
                raise ValueError("A finding has missing evidence references")
        return self


def _digest(data: object) -> str:
    encoded = json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


class _Collector:
    def __init__(self, observed_at: datetime):
        self.observed_at = observed_at
        self.findings: list[Finding] = []
        self.evidence: dict[str, EvidenceRecord] = {}
        self.counts: Counter[str] = Counter()

    def add(
        self,
        category: Category,
        kind: FindingKind,
        scope: str,
        value: str | int | bool,
        data: JsonValue,
        source: str,
        summary: str = "",
        uncertainty: Literal["observed", "potential", "unknown"] = "observed",
    ) -> None:
        raw = data if isinstance(data, dict) else {}
        citation = raw.get("citation") or {}
        reference = citation if isinstance(citation, dict) else {}
        source_at = raw.get("published_at") or reference.get("published_at")
        evidence_id = "evidence-" + _digest([category, scope, source, data])
        self.evidence[evidence_id] = EvidenceRecord(
            id=evidence_id,
            source=source,
            reference=reference,
            data=data,
            source_at=str(source_at) if source_at else None,
        )
        base = _digest([category, kind, scope, value, evidence_id])
        self.counts[base] += 1
        self.findings.append(
            Finding(
                id=f"finding-{base}-{self.counts[base]}",
                category=category,
                kind=kind,
                scope=scope,
                value=value,
                summary=summary,
                evidence_refs=(evidence_id,),
                source=source,
                source_at=self.evidence[evidence_id].source_at,
                observed_at=self.observed_at,
                uncertainty=uncertainty,
            )
        )


def _state(response: dict) -> AssessmentState:
    result = response.get("result") or {}
    if response.get("status") == "error" or not result:
        return "not_assessed"
    if result.get("skipped"):
        return "skipped"
    if response.get("fallbacks") or response.get("source") == "fallback":
        return "partial"
    return "completed"


def _assessment(
    records: _Collector,
    category: Category,
    scope: str,
    state: AssessmentState,
    response: dict,
) -> None:
    result = response.get("result") or {}
    summary = ""
    if state == "not_assessed":
        label = "Sanctions screening" if scope == "sanctions" else f"{scope.title()} assessment"
        summary = f"⚠️ {label} did not run"
    elif state == "skipped":
        summary = f"⚠️ {scope.title()} assessment skipped: {result.get('reason', 'not assessed')}"
    elif state == "partial":
        summary = f"⚠️ {scope.title()} assessment has missing evidence"
    data = {
        "state": state,
        "fallbacks": sorted(response.get("fallbacks", [])),
        "reason": result.get("reason"),
    }
    records.add(
        category,
        "assessment",
        scope,
        state,
        data,
        response.get("source", "unknown"),
        summary,
        "observed" if state == "completed" else "unknown",
    )


def _identity(records: _Collector, result: dict, source: str) -> None:
    for discrepancy in result.get("discrepancies", []):
        severity = discrepancy.get("severity", "unknown")
        if severity not in ("high", "medium", "low"):
            severity = "unknown"
        records.add(
            "identity",
            "discrepancy",
            "identity",
            severity,
            discrepancy,
            source,
            f"Identity discrepancy: {discrepancy.get('field', 'unknown field')} ({severity})",
            "unknown" if severity == "unknown" else "observed",
        )


def _screening(records: _Collector, response: dict, state: AssessmentState) -> None:
    result = response.get("result") or {}
    source = response.get("source", "unknown")
    for scope, tool, kind in SCREENING_CHECKS:
        check_state = state
        if state == "partial" and response.get("fallbacks"):
            check_state = "not_assessed" if tool in response["fallbacks"] else "completed"
        _assessment(records, "screening", scope, check_state, response)
        if check_state in ("not_assessed", "skipped") or not result.get(f"{scope}_hit"):
            continue
        hits = [f for f in result.get("findings", []) if f.get("type") == scope]
        # A recorded flag without a passage is evidence of a reported flag, not a new citation.
        for hit in hits or [{"type": scope, "reported_hit": True}]:
            summary = {
                "sanctions": "⚠️ Potential sanctions match: a person must confirm or clear it",
                "pep": f"PEP identified: {hit.get('match', '')[:100]}",
                "adverse_media": "Adverse media coverage found — review required",
            }[scope]
            records.add("screening", kind, scope, True, hit, source, summary, "potential")


def _corporate(records: _Collector, result: dict, source: str) -> None:
    flags = result.get("risk_flags", [])
    evidence = result.get("risk_flag_evidence")
    if evidence is None:
        # Recorded profiles may contain a claim without an observed ownership node.
        evidence = [{"reported_flag": flag} for flag in flags]
    for flag, observation in zip(flags, evidence, strict=True):
        records.add("corporate", "corporate_flag", "corporate", True, observation, source, flag)
    depth = result.get("ubo_chain", {}).get("depth", 0)
    if depth > 3:
        records.add(
            "corporate",
            "ownership_depth",
            "corporate",
            depth,
            result["ubo_chain"],
            source,
            f"Ownership chain depth exceeds three levels ({depth})",
        )


def _transaction(records: _Collector, result: dict, source: str) -> None:
    flags: tuple[Literal["structuring", "layering"], ...] = ("structuring", "layering")
    for flag in flags:
        if result.get(f"{flag}_flag"):
            data = {"pattern": flag, "transactions": result.get("anomalous_transactions", [])}
            if "pattern_evidence" in result:
                data = {"pattern": flag, "observation": result["pattern_evidence"]}
            records.add(
                "transaction",
                flag,
                "transaction",
                True,
                data,
                source,
                f"Transaction {flag} pattern detected",
            )
    for hit in result.get("typology_hits", []):
        label = hit.get("typology", "Unnamed typology") if isinstance(hit, dict) else hit
        records.add(
            "transaction",
            "typology",
            "transaction",
            True,
            hit,
            source,
            f"Transaction typology: {label}",
            "potential",
        )


def collect_findings(upstream: dict, observed_at: datetime | None = None) -> FindingSet:
    """Read facts from the four responses; all cached score fields are deliberately ignored."""
    records = _Collector(observed_at or datetime.now(UTC))
    builders = {"identity": _identity, "corporate": _corporate, "transaction": _transaction}
    for category in CATEGORIES:
        response = upstream.get(category) or {}
        state = _state(response)
        if category == "screening":
            _screening(records, response, state)
            continue
        _assessment(records, category, category, state, response)
        if state in ("completed", "partial"):
            builders[category](records, response["result"], response.get("source", "unknown"))
    return FindingSet(findings=tuple(records.findings), evidence=records.evidence)


def key_findings(findings: tuple[Finding, ...]) -> list[str]:
    """Legacy display strings, with the established summary facts first, then remaining facts."""
    order = {
        "pep_match": 0,
        "adverse_media_match": 1,
        "sanctions_match": 2,
        "corporate_flag": 3,
        "structuring": 4,
    }
    summaries = [
        f.summary for f in sorted(findings, key=lambda f: order.get(f.kind, 5)) if f.summary
    ]
    return list(dict.fromkeys(summaries)) or [
        "No high-risk indicators found in the assessed checks; human review remains pending"
    ]
