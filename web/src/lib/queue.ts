// The cases queue: each demo case's last run in this browser, kept in localStorage by the case's
// position in DEMO_CASES, never by its name. Runs expire after a day, as the API's reports do.

import type { AssessmentRequest } from "./api";
import { isSanctionsHold } from "./case";
import { DEMO_CASES } from "./demo";
import type { Report } from "./report";

export const DAY_MS = 24 * 60 * 60 * 1000;

const KEY = "argus:queue";

export interface QueueEntry {
  reportId: string;
  tier?: string;
  score?: number;
  /** Whether a sanctions hold set the tier, and a rule requires enhanced due diligence: the demo
   * review's rules depend on both. */
  hold?: boolean;
  edd?: boolean;
  /** When the run was recorded, in milliseconds since the epoch. */
  at: number;
}

export function browserStorage(): Storage | undefined {
  try {
    return typeof window === "undefined" ? undefined : window.localStorage;
  } catch {
    return undefined; // storage blocked by the browser
  }
}

/** Same-tab updates; other tabs hear the browser's own "storage" event. */
export const QUEUE_EVENT = "argus:queue";

/** The stored queue as text, for useSyncExternalStore; empty when nothing can be read. */
export function rawQueue(storage: Storage | undefined = browserStorage()): string {
  try {
    return storage?.getItem(KEY) ?? "";
  } catch {
    return "";
  }
}

function read(storage?: Storage): Record<number, QueueEntry> {
  try {
    const parsed: unknown = JSON.parse(storage?.getItem(KEY) ?? "{}");
    return parsed && typeof parsed === "object" ? (parsed as Record<number, QueueEntry>) : {};
  } catch {
    return {};
  }
}

function write(entries: Record<number, QueueEntry>, storage?: Storage): boolean {
  if (!storage) return false;
  try {
    storage.setItem(KEY, JSON.stringify(entries));
    if (typeof window !== "undefined") window.dispatchEvent(new Event(QUEUE_EVENT));
    return true;
  } catch {
    return false; // storage full or blocked
  }
}

/** The runs recorded in this browser in the last day, by demo case position. */
export function loadQueue(
  storage: Storage | undefined = browserStorage(),
  now: number = Date.now(),
): Record<number, QueueEntry> {
  return Object.fromEntries(
    Object.entries(read(storage)).filter(
      ([, entry]) => typeof entry?.reportId === "string" && now - entry.at <= DAY_MS,
    ),
  );
}

/**
 * Records a demo case's latest run; false when this browser does not keep it, either because
 * storage is unavailable or because a newer run of the case is already kept.
 */
export function recordRun(
  caseIndex: number,
  entry: QueueEntry,
  storage: Storage | undefined = browserStorage(),
): boolean {
  const entries = read(storage);
  const kept = entries[caseIndex];
  if (kept && kept.reportId !== entry.reportId && kept.at > entry.at) return false;
  return write({ ...entries, [caseIndex]: entry }, storage);
}

/**
 * The queue entry for a finished report, dated when the report was generated: reopening an old
 * report neither restarts its 24 hours nor makes it the case's latest run.
 */
export function runEntry(
  reportId: string,
  report: Pick<Report, "generated_at" | "risk_summary">,
  now: number = Date.now(),
): QueueEntry {
  const generated = Date.parse(report.generated_at ?? "");
  return {
    reportId,
    tier: report.risk_summary?.overall_risk_tier,
    score: report.risk_summary?.overall_risk_score,
    hold: isSanctionsHold(report),
    edd: report.risk_summary?.edd_required === true,
    at: Number.isFinite(generated) ? generated : now,
  };
}

/** Forgets a report the API no longer has, so its case shows as not run. */
export function forgetReport(reportId: string, storage: Storage | undefined = browserStorage()) {
  const entries = read(storage);
  const kept = Object.fromEntries(
    Object.entries(entries).filter(([, entry]) => entry?.reportId !== reportId),
  );
  if (Object.keys(kept).length !== Object.keys(entries).length) write(kept, storage);
}

/** The demo case a report is about, by name and jurisdiction. */
export function demoCaseIndex(entity?: {
  name?: string;
  jurisdiction?: string;
}): number | undefined {
  if (!entity) return undefined;
  const index = DEMO_CASES.findIndex(
    (demo) => demo.entity_name === entity.name && demo.jurisdiction === entity.jurisdiction,
  );
  return index === -1 ? undefined : index;
}

const TIER_RANK: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
const NOT_RUN = 5;

export interface QueueRow {
  index: number;
  request: AssessmentRequest;
  entry?: QueueEntry;
}

/** The demo cases, riskiest run first, cases not run last, each group by name. */
export function queueRows(entries: Record<number, QueueEntry>): QueueRow[] {
  const rank = (row: QueueRow) =>
    row.entry ? (TIER_RANK[row.entry.tier?.toUpperCase() ?? ""] ?? 4) : NOT_RUN;
  return DEMO_CASES.map((request, index) => ({ index, request, entry: entries[index] })).sort(
    (a, b) => rank(a) - rank(b) || a.request.entity_name.localeCompare(b.request.entity_name),
  );
}
