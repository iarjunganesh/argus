// The demo review's rules: who may take which step, in which order, for which case. Nothing here
// is sent anywhere; the steps are kept in this browser (review-store.ts).

import { isSanctionsHold } from "./case";
import type { Report } from "./report";
import type { Role, Step } from "./review-store";

export type MatchAction = "confirm" | "clear" | "escalate_match";
export type CaseAction = "approve" | "approve_edd" | "decline" | "escalate";
export type ApproverAction = "sign_off" | "return";
export type ReviewAction = MatchAction | CaseAction | ApproverAction;

export type ReviewState =
  "awaiting_analyst" | "awaiting_approver" | "returned" | "decided" | "escalated";

export interface ReviewContext {
  /** A potential sanctions match holds the case until a person resolves it. */
  hold: boolean;
  /** A rule requires enhanced due diligence, so plain approval is not offered. */
  edd: boolean;
  tier?: string;
}

export const ACTION_LABELS: Record<ReviewAction, string> = {
  confirm: "Confirm: true match",
  clear: "Clear: false positive",
  escalate_match: "Escalate the match",
  approve: "Approve",
  approve_edd: "Approve with enhanced due diligence",
  decline: "Decline",
  escalate: "Escalate",
  sign_off: "Sign off",
  return: "Return to the analyst",
};

export const STATE_LABELS: Record<ReviewState, string> = {
  awaiting_analyst: "Awaiting analyst",
  awaiting_approver: "Awaiting approver",
  returned: "Returned to the analyst",
  decided: "Decided",
  escalated: "Escalated",
};

const MATCH_ACTIONS: readonly ReviewAction[] = ["confirm", "clear", "escalate_match"];

export function isMatchAction(action: ReviewAction): action is MatchAction {
  return MATCH_ACTIONS.includes(action);
}

/** Only HIGH and CRITICAL cases need a second person's sign-off. */
const needsSignOff = (ctx: ReviewContext) => ctx.tier === "HIGH" || ctx.tier === "CRITICAL";

export function reviewContext(report: Report): ReviewContext {
  return {
    hold: isSanctionsHold(report),
    edd: report.risk_summary?.edd_required === true,
    tier: report.risk_summary?.overall_risk_tier?.toUpperCase(),
  };
}

interface Progress {
  state: ReviewState;
  match?: "confirm" | "clear";
}

function open(
  progress: Progress,
  ctx: ReviewContext,
): { allowed: ReviewAction[]; by: Role | null } {
  const { state, match } = progress;
  if (state === "decided" || state === "escalated") return { allowed: [], by: null };
  if (state === "awaiting_approver") return { allowed: ["sign_off", "return"], by: "approver" };
  let allowed: ReviewAction[];
  if (ctx.hold && !match) allowed = [...MATCH_ACTIONS];
  else if (match === "confirm") allowed = ["decline", "escalate"];
  else if (ctx.edd) allowed = ["approve_edd", "decline", "escalate"];
  else allowed = ["approve", "approve_edd", "decline", "escalate"];
  return { allowed, by: "analyst" };
}

function refusal(step: Step, progress: Progress, ctx: ReviewContext): string | undefined {
  const { allowed, by } = open(progress, ctx);
  if (!allowed.includes(step.action)) return "That step is not open in this review now.";
  if (step.reviewer !== by) {
    return by === "approver"
      ? "Only the approver can take this step. Switch the role to Approver."
      : "Only the analyst can take this step. Switch the role to Analyst.";
  }
  if (step.action !== "sign_off" && !step.rationale.trim()) {
    return "Give a reason: the review records why each step was taken.";
  }
  return undefined;
}

function apply(progress: Progress, action: ReviewAction, ctx: ReviewContext): Progress {
  switch (action) {
    case "confirm":
    case "clear":
      return { ...progress, match: action };
    case "escalate_match":
    case "escalate":
      return { ...progress, state: "escalated" };
    case "sign_off":
      return { ...progress, state: "decided" };
    case "return":
      return { ...progress, state: "returned" };
    default:
      return { ...progress, state: needsSignOff(ctx) ? "awaiting_approver" : "decided" };
  }
}

/** Replays the rules over the steps, skipping any they would refuse (storage is not trusted). */
function replay(steps: Step[], ctx: ReviewContext): Progress {
  return steps.reduce<Progress>(
    (progress, step) =>
      refusal(step, progress, ctx) ? progress : apply(progress, step.action, ctx),
    { state: "awaiting_analyst" },
  );
}

/** Where the review stands, which steps are open and which role takes them. */
export function reviewState(
  steps: Step[],
  ctx: ReviewContext,
): { state: ReviewState; allowed: ReviewAction[]; by: Role | null } {
  const progress = replay(steps, ctx);
  return { state: progress.state, ...open(progress, ctx) };
}

/** The steps with this one added, or why the rules refuse it. */
export function addStep(steps: Step[], step: Step, ctx: ReviewContext): Step[] | { error: string } {
  const error = refusal(step, replay(steps, ctx), ctx);
  return error ? { error } : [...steps, { ...step, rationale: step.rationale.trim() }];
}
