// The report as a case file: the score's working, the findings filed under their dimensions,
// and the sanctions listing behind a match. Everything here reads the report as the API returns
// it; nothing is computed that the API does not already decide.

import {
  DIMENSIONS,
  NOT_REPORTED,
  type AuditTrace,
  type Dimension,
  type EvidenceRecord,
  type Finding,
  type Report,
} from "./report";

export type DimensionKey = (typeof DIMENSIONS)[number]["key"];

export interface WorkingRow {
  key: DimensionKey;
  label: string;
  score?: number;
  /** As a fraction: 0.2 for "20%". */
  weight?: number;
  points?: number;
  tier?: string;
}

const round1 = (value: number) => Math.round(value * 10) / 10;

function parseWeight(weight?: string): number | undefined {
  const match = weight?.trim().match(/^(\d+(?:\.\d+)?)\s*%$/);
  return match ? Number(match[1]) / 100 : undefined;
}

/** Each dimension's score times its weight, and their sum: the overall score. */
export function scoreWorking(dimensions?: Record<string, Dimension>): {
  rows: WorkingRow[];
  total?: number;
} {
  const rows = DIMENSIONS.map(({ key, label }): WorkingRow => {
    const dimension = dimensions?.[key] ?? {};
    const score = Number.isFinite(dimension.score) ? dimension.score : undefined;
    const weight = parseWeight(dimension.weight);
    const points = score !== undefined && weight !== undefined ? round1(score * weight) : undefined;
    return { key, label, score, weight, points, tier: dimension.tier };
  });
  const complete = rows.every((row) => row.points !== undefined);
  const total = complete
    ? round1(rows.reduce((sum, row) => sum + (row.points ?? 0), 0))
    : undefined;
  return { rows, total };
}

const DIMENSION_OF: Record<Finding["category"], DimensionKey> = {
  identity: "identity",
  screening: "screening",
  corporate: "corporate_ubo",
  transaction: "transaction",
};

const UNCERTAINTY_ORDER: Record<Finding["uncertainty"], number> = {
  potential: 0,
  unknown: 1,
  observed: 2,
};

const emptyLists = <T>() =>
  Object.fromEntries(DIMENSIONS.map(({ key }) => [key, [] as T[]])) as Record<DimensionKey, T[]>;

/**
 * The findings under their dimensions, the ones a person must act on first. A check that ran to
 * completion records no fact of its own, so it is listed by name; a check that did not run, ran
 * in part or was skipped stays a finding, because the analyst must see it.
 */
export function groupFindings(findings?: Finding[]): {
  byDimension: Record<DimensionKey, Finding[]>;
  checksCompleted: Record<DimensionKey, string[]>;
} {
  const byDimension = emptyLists<Finding>();
  const checksCompleted = emptyLists<string>();
  for (const finding of findings ?? []) {
    const key = DIMENSION_OF[finding.category];
    if (!key) continue;
    if (finding.kind === "assessment" && finding.value === "completed") {
      checksCompleted[key].push(finding.scope);
    } else {
      byDimension[key].push(finding);
    }
  }
  for (const list of Object.values(byDimension)) {
    list.sort((a, b) => UNCERTAINTY_ORDER[a.uncertainty] - UNCERTAINTY_ORDER[b.uncertainty]);
  }
  return { byDimension, checksCompleted };
}

const UNCERTAINTY: Record<Finding["uncertainty"], string> = {
  observed: "Observed",
  potential: "Potential: a person must confirm",
  unknown: "Unknown: not assessed",
};

export function uncertaintyLabel(value: Finding["uncertainty"]): string {
  return UNCERTAINTY[value] ?? NOT_REPORTED;
}

/** The finding's summary, without the warning sign some summaries start with. */
export function findingTitle(finding: Finding): string {
  return finding.summary.replace(/^⚠️\s*/u, "");
}

const CHECKS: Record<string, string> = {
  identity: "Identity",
  sanctions: "Sanctions",
  pep: "PEP",
  adverse_media: "Adverse media",
  corporate: "Corporate",
  transaction: "Transaction",
};

export function checkLabel(scope: string): string {
  return CHECKS[scope] ?? scope;
}

/** A time for people: date and minutes, in the reader's zone unless one is given. */
export function formatTime(iso?: string | null, locale?: string, timeZone?: string): string {
  if (!iso) return NOT_REPORTED;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return NOT_REPORTED;
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone,
  }).format(date);
}

/** The recommended actions, leaving out any that is already listed as an obligation. */
export function actionsBesidesObligations(actions?: string[], obligations?: string[]): string[] {
  const listed = new Set(obligations ?? []);
  return (actions ?? []).filter((action) => !listed.has(action));
}

/** Whether a potential sanctions match, not the score band, sets the tier. */
export function isSanctionsHold(report: Report): boolean {
  return report.risk_summary?.tier_basis === "sanctions_match";
}

/** One line for a finished run: how many agents, how long, how many from recorded profiles. */
export function investigationSummary(trace?: AuditTrace, seconds?: number): string {
  const agents = trace?.agents_invoked?.length ?? 0;
  const recorded = Object.values(trace?.agent_sources ?? {}).filter(
    (source) => source === "demo_profile",
  ).length;
  let line = `${agents} ${agents === 1 ? "agent" : "agents"} finished`;
  if (seconds !== undefined) line += ` in ${seconds} s`;
  if (recorded) line += `; ${recorded} from recorded demo profiles`;
  return line;
}

export interface ListingSide {
  programme?: string;
  entryId?: string;
  active?: boolean;
  match?: string;
  /** The screening source's own match score, as it reported it. */
  sourceScore?: number;
  document?: string;
}

const text = (value: unknown) => (typeof value === "string" ? value : undefined);

/** The listing behind the first potential sanctions match, from its evidence record. */
export function sanctionsListing(report: Report): ListingSide | undefined {
  const finding = report.findings?.find((f) => f.kind === "sanctions_match");
  if (!finding) return undefined;
  const record = finding.evidence_refs.map((ref) => report.evidence?.[ref]).find(Boolean);
  const reference = record?.reference ?? {};
  const data = (record?.data ?? {}) as Record<string, unknown>;
  return {
    programme: text(reference.program),
    entryId: text(reference.snippet_id),
    active: typeof reference.is_active === "boolean" ? reference.is_active : undefined,
    match: text(data.match),
    sourceScore: typeof data.confidence === "number" ? data.confidence : undefined,
    document: text(reference.document),
  };
}

function fieldLabel(key: string): string {
  const words = key.replace(/_/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function fieldValue(value: unknown): string {
  if (value === null || value === undefined) return "None";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  return JSON.stringify(value);
}

/** An evidence record's reference and data fields, labelled for people, in their order. */
export function evidenceFields(record: EvidenceRecord): { label: string; value: string }[] {
  const reference = Object.entries(record.reference ?? {});
  const data =
    record.data !== null && typeof record.data === "object" && !Array.isArray(record.data)
      ? Object.entries(record.data as Record<string, unknown>)
      : [["data", record.data] as const];
  return [...reference, ...data].map(([key, value]) => ({
    label: fieldLabel(key),
    value: fieldValue(value),
  }));
}
