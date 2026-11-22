// The demo review's steps and the visitor's role, kept in localStorage and sent nowhere. Steps are
// keyed by report ID, never by the entity's name, and expire a day after the newest one, as the
// API's reports do. Each step uses the field names of the report's empty `decision_record` slots
// (`reviewer`, `decided_at`, `rationale`), so a server-side review could take them over.

import { browserStorage, DAY_MS } from "./queue";
import type { ReviewAction } from "./review";

export type Role = "analyst" | "approver";

export interface Step {
  /** The role that took the step; the demo cannot tell whether two roles are two people. */
  reviewer: Role;
  action: ReviewAction;
  rationale: string;
  /** ISO 8601, like the report's own times. */
  decided_at: string;
}

const ROLE_KEY = "argus:role";

/** Same-tab role changes; other tabs hear the browser's own "storage" event. */
export const ROLE_EVENT = "argus:role";

const stepsKey = (reportId: string) => `argus:review:${reportId}`;

const isRole = (value: unknown): value is Role => value === "analyst" || value === "approver";

function isStep(value: unknown): value is Step {
  const step = value as Partial<Step> | null;
  return (
    typeof step === "object" &&
    step !== null &&
    isRole(step.reviewer) &&
    typeof step.action === "string" &&
    typeof step.rationale === "string" &&
    typeof step.decided_at === "string"
  );
}

function parse(text: string | null): Step[] {
  try {
    const parsed: unknown = JSON.parse(text ?? "[]");
    return Array.isArray(parsed) ? parsed.filter(isStep) : [];
  } catch {
    return [];
  }
}

/** A report's review steps in this browser; `kept` is false when this browser keeps nothing. */
export function loadSteps(
  reportId: string,
  storage: Storage | undefined = browserStorage(),
  now: number = Date.now(),
): { steps: Step[]; kept: boolean } {
  if (!storage) return { steps: [], kept: false };
  try {
    const steps = parse(storage.getItem(stepsKey(reportId)));
    const newest = Math.max(...steps.map((step) => Date.parse(step.decided_at) || 0));
    if (steps.length && now - newest > DAY_MS) {
      storage.removeItem(stepsKey(reportId));
      return { steps: [], kept: true };
    }
    return { steps, kept: true };
  } catch {
    return { steps: [], kept: false }; // storage blocked by the browser
  }
}

/** Keeps a report's review steps; false when this browser does not keep them. */
export function saveSteps(
  reportId: string,
  steps: Step[],
  storage: Storage | undefined = browserStorage(),
): boolean {
  if (!storage) return false;
  try {
    storage.setItem(stepsKey(reportId), JSON.stringify(steps));
    return true;
  } catch {
    return false; // storage full or blocked
  }
}

/** Forgets the review of a report the API no longer has. */
export function forgetSteps(reportId: string, storage: Storage | undefined = browserStorage()) {
  try {
    storage?.removeItem(stepsKey(reportId));
  } catch {
    // storage blocked: nothing was kept
  }
}

/** The visitor's role in the demo review; the analyst unless the approver was chosen. */
export function loadRole(storage: Storage | undefined = browserStorage()): Role {
  try {
    const role = storage?.getItem(ROLE_KEY);
    return isRole(role) ? role : "analyst";
  } catch {
    return "analyst";
  }
}

/** Keeps the chosen role; false when this browser does not keep it. */
export function saveRole(role: Role, storage: Storage | undefined = browserStorage()): boolean {
  if (!storage) return false;
  try {
    storage.setItem(ROLE_KEY, role);
    if (typeof window !== "undefined") window.dispatchEvent(new Event(ROLE_EVENT));
    return true;
  } catch {
    return false;
  }
}
