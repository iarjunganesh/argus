"use client";

// The demo review's state for React: the visitor's role and a report's steps, read from this
// browser's storage after hydration, and kept for the open page when the browser blocks storage.

import { useCallback, useMemo, useSyncExternalStore } from "react";

import type { QueueRow } from "@/lib/queue";
import type { Report } from "@/lib/report";
import {
  acceptedSteps,
  addStep,
  entryReviewState,
  reviewContext,
  reviewState,
  type ReviewAction,
  type ReviewState,
} from "@/lib/review";
import {
  loadRole,
  loadSteps,
  REVIEW_EVENT,
  ROLE_EVENT,
  saveRole,
  saveSteps,
  type Role,
  type Step,
} from "@/lib/review-store";

// What this page could not keep because the browser blocks storage; gone on reload.
const unsavedSteps = new Map<string, Step[]>();
let unsavedRole: Role | null = null;

function subscribeTo(event: string) {
  return (onChange: () => void) => {
    window.addEventListener("storage", onChange);
    window.addEventListener(event, onChange);
    return () => {
      window.removeEventListener("storage", onChange);
      window.removeEventListener(event, onChange);
    };
  };
}

const subscribeRole = subscribeTo(ROLE_EVENT);
const subscribeReview = subscribeTo(REVIEW_EVENT);

/** The visitor's role in the demo review, and a setter that keeps it where it can. */
export function useRole(): [Role, (role: Role) => void] {
  const role = useSyncExternalStore<Role>(
    subscribeRole,
    () => unsavedRole ?? loadRole(),
    () => "analyst",
  );
  const setRole = useCallback((next: Role) => {
    if (saveRole(next)) {
      unsavedRole = null;
    } else {
      unsavedRole = next;
      window.dispatchEvent(new Event(ROLE_EVENT));
    }
  }, []);
  return [role, setRole];
}

function stepsSnapshot(reportId: string): string {
  const unsaved = unsavedSteps.get(reportId);
  return JSON.stringify(unsaved ? { steps: unsaved, kept: false } : loadSteps(reportId));
}

export interface Review {
  /** The steps the rules accept, in order. */
  steps: Step[];
  state: ReviewState;
  allowed: ReviewAction[];
  by: Role | null;
  /** False when this browser blocks storage: the review lasts as long as the page. */
  kept: boolean;
  role: Role;
  /** Takes a step in the current role; returns why the rules refuse it, if they do. */
  add: (action: ReviewAction, rationale: string) => string | undefined;
}

/** A report's demo review in this browser. */
export function useReview(report: Report): Review {
  const reportId = report.report_id ?? "";
  const raw = useSyncExternalStore(
    subscribeReview,
    () => stepsSnapshot(reportId),
    () => "",
  );
  const [role] = useRole();
  const ctx = useMemo(() => reviewContext(report), [report]);
  const stored = useMemo<{ steps: Step[]; kept: boolean }>(
    () => (raw ? JSON.parse(raw) : { steps: [], kept: true }),
    [raw],
  );
  const add = useCallback(
    (action: ReviewAction, rationale: string) => {
      const step = { reviewer: role, action, rationale, decided_at: new Date().toISOString() };
      const next = addStep(stored.steps, step, ctx);
      if ("error" in next) return next.error;
      if (saveSteps(reportId, next)) {
        unsavedSteps.delete(reportId);
      } else {
        unsavedSteps.set(reportId, next);
        window.dispatchEvent(new Event(REVIEW_EVENT));
      }
      return undefined;
    },
    [stored.steps, role, ctx, reportId],
  );
  return {
    steps: acceptedSteps(stored.steps, ctx),
    ...reviewState(stored.steps, ctx),
    kept: stored.kept,
    role,
    add,
  };
}

/** Each queued run's review state in this browser, by demo case position. */
export function useQueueReviewStates(rows: QueueRow[]): Record<number, ReviewState> {
  const raw = useSyncExternalStore(
    subscribeReview,
    () =>
      JSON.stringify(
        Object.fromEntries(
          rows.flatMap((row) => (row.entry ? [[row.index, entryReviewState(row.entry)]] : [])),
        ),
      ),
    () => "{}",
  );
  return useMemo(() => JSON.parse(raw) as Record<number, ReviewState>, [raw]);
}
