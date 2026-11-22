import { describe, expect, it } from "vitest";

import type { Report } from "./report";
import {
  acceptedSteps,
  ACTION_LABELS,
  addStep,
  entryReviewState,
  isMatchAction,
  reviewContext,
  reviewState,
  ROLE_LABELS,
  STATE_LABELS,
  type ReviewAction,
  type ReviewContext,
} from "./review";
import { saveSteps, type Role, type Step } from "./review-store";
import { memoryStorage } from "./test-storage";

const CAYMAN: ReviewContext = { hold: true, edd: true, tier: "CRITICAL" };
const JANE: ReviewContext = { hold: false, edd: false, tier: "LOW" };
const PAYMENTS: ReviewContext = { hold: false, edd: true, tier: "HIGH" };
const HOLDINGS: ReviewContext = { hold: false, edd: false, tier: "MEDIUM" };

const step = (action: ReviewAction, reviewer: Role = "analyst", rationale = "A reason."): Step => ({
  reviewer,
  action,
  rationale,
  decided_at: "2026-11-22T12:00:00.000Z",
});

const CASE_ACTIONS: ReviewAction[] = ["approve", "approve_edd", "decline", "escalate"];

describe("reviewState", () => {
  it("asks the analyst to resolve a sanctions match first", () => {
    expect(reviewState([], CAYMAN)).toEqual({
      state: "awaiting_analyst",
      allowed: ["confirm", "clear", "escalate_match"],
      by: "analyst",
    });
  });

  it("closes the review when the match or the case is escalated", () => {
    const closed = { state: "escalated", allowed: [], by: null };
    expect(reviewState([step("escalate_match")], CAYMAN)).toEqual(closed);
    expect(reviewState([step("escalate")], JANE)).toEqual(closed);
    expect(reviewState([step("clear"), step("escalate")], CAYMAN)).toEqual(closed);
  });

  it("leaves only decline or escalate after a confirmed match", () => {
    expect(reviewState([step("confirm")], CAYMAN)).toEqual({
      state: "awaiting_analyst",
      allowed: ["decline", "escalate"],
      by: "analyst",
    });
  });

  it("offers every case decision without a hold or after a cleared match", () => {
    expect(reviewState([], JANE).allowed).toEqual(CASE_ACTIONS);
    expect(reviewState([], JANE).by).toBe("analyst");
  });

  it("offers approval only with enhanced due diligence when a rule requires it", () => {
    expect(reviewState([step("clear")], CAYMAN).allowed).toEqual([
      "approve_edd",
      "decline",
      "escalate",
    ]);
    expect(reviewState([], PAYMENTS).allowed).toEqual(["approve_edd", "decline", "escalate"]);
  });

  it("sends a HIGH or CRITICAL decision to the approver", () => {
    const waiting = { state: "awaiting_approver", allowed: ["sign_off", "return"], by: "approver" };
    expect(reviewState([step("clear"), step("approve_edd")], CAYMAN)).toEqual(waiting);
    expect(reviewState([step("confirm"), step("decline")], CAYMAN)).toEqual(waiting);
    expect(reviewState([step("decline")], PAYMENTS)).toEqual(waiting);
  });

  it("decides a LOW or MEDIUM case without a second sign-off", () => {
    const decided = { state: "decided", allowed: [], by: null };
    expect(reviewState([step("approve")], JANE)).toEqual(decided);
    expect(reviewState([step("decline")], HOLDINGS)).toEqual(decided);
  });

  it("decides the case when the approver signs off", () => {
    expect(
      reviewState([step("clear"), step("approve_edd"), step("sign_off", "approver", "")], CAYMAN),
    ).toEqual({ state: "decided", allowed: [], by: null });
  });

  it("returns the case to the analyst, whose match step stands", () => {
    expect(
      reviewState([step("clear"), step("approve_edd"), step("return", "approver")], CAYMAN),
    ).toEqual({
      state: "returned",
      allowed: ["approve_edd", "decline", "escalate"],
      by: "analyst",
    });
    expect(
      reviewState([step("confirm"), step("decline"), step("return", "approver")], CAYMAN).allowed,
    ).toEqual(["decline", "escalate"]);
  });

  it("goes back to the approver after the analyst decides a returned case again", () => {
    const steps = [step("clear"), step("approve_edd"), step("return", "approver"), step("decline")];
    expect(reviewState(steps, CAYMAN).state).toBe("awaiting_approver");
  });

  it("skips stored steps the rules would refuse", () => {
    expect(reviewState([step("sign_off", "analyst")], CAYMAN)).toEqual(reviewState([], CAYMAN));
    expect(reviewState([step("approve")], CAYMAN)).toEqual(reviewState([], CAYMAN));
    expect(reviewState([step("clear", "approver")], CAYMAN)).toEqual(reviewState([], CAYMAN));
    expect(reviewState([step("approve", "analyst", " ")], JANE)).toEqual(reviewState([], JANE));
  });
});

describe("addStep", () => {
  it("adds an allowed step with its reason trimmed, leaving the old list as it was", () => {
    const before = [step("clear")];
    const after = addStep(before, step("approve_edd", "analyst", "  Onboard with EDD. "), CAYMAN);
    expect(after).toEqual([step("clear"), step("approve_edd", "analyst", "Onboard with EDD.")]);
    expect(before).toHaveLength(1);
  });

  it("refuses a step the review has not reached", () => {
    expect(addStep([], step("approve_edd"), CAYMAN)).toEqual({
      error: "That step is not open in this review now.",
    });
    expect(addStep([step("approve")], step("decline"), JANE)).toEqual({
      error: "That step is not open in this review now.",
    });
  });

  it("refuses a step taken in the wrong role", () => {
    const waiting = [step("clear"), step("approve_edd")];
    expect(addStep(waiting, step("sign_off", "analyst", ""), CAYMAN)).toEqual({
      error: "Only the approver can take this step. Switch the role to Approver.",
    });
    expect(addStep([], step("clear", "approver"), CAYMAN)).toEqual({
      error: "Only the analyst can take this step. Switch the role to Analyst.",
    });
  });

  it("requires a reason for every step except a sign-off", () => {
    const refused = { error: "Give a reason: the review records why each step was taken." };
    expect(addStep([], step("clear", "analyst", ""), CAYMAN)).toEqual(refused);
    expect(addStep([], step("approve", "analyst", "   "), JANE)).toEqual(refused);
    const waiting = [step("clear"), step("approve_edd")];
    expect(addStep(waiting, step("return", "approver", ""), CAYMAN)).toEqual(refused);
    expect(addStep(waiting, step("sign_off", "approver", ""), CAYMAN)).toHaveLength(3);
  });
});

describe("reviewContext", () => {
  it("reads the hold, the enhanced due diligence and the tier from the report", () => {
    const report: Report = {
      risk_summary: {
        overall_risk_tier: "critical",
        tier_basis: "sanctions_match",
        edd_required: true,
      },
    };
    expect(reviewContext(report)).toEqual({ hold: true, edd: true, tier: "CRITICAL" });
    expect(reviewContext({})).toEqual({ hold: false, edd: false, tier: undefined });
  });
});

describe("labels", () => {
  it("names each action and state in words", () => {
    expect(ACTION_LABELS).toEqual({
      confirm: "Confirm: true match",
      clear: "Clear: false positive",
      escalate_match: "Escalate the match",
      approve: "Approve",
      approve_edd: "Approve with enhanced due diligence",
      decline: "Decline",
      escalate: "Escalate",
      sign_off: "Sign off",
      return: "Return to the analyst",
    });
    expect(STATE_LABELS).toEqual({
      awaiting_analyst: "Awaiting analyst",
      awaiting_approver: "Awaiting approver",
      returned: "Returned to the analyst",
      decided: "Decided",
      escalated: "Escalated",
    });
    expect(ROLE_LABELS).toEqual({ analyst: "Analyst", approver: "Approver" });
  });

  it("tells the match's actions from the case's", () => {
    expect(isMatchAction("confirm")).toBe(true);
    expect(isMatchAction("clear")).toBe(true);
    expect(isMatchAction("escalate_match")).toBe(true);
    expect(isMatchAction("escalate")).toBe(false);
    expect(isMatchAction("sign_off")).toBe(false);
  });
});

describe("entryReviewState", () => {
  it("reads a queued run's review state from this browser", () => {
    const storage = memoryStorage();
    const now = Date.parse("2026-11-22T12:05:00Z");
    const cayman = { reportId: "argus-rpt-a", tier: "CRITICAL", hold: true, edd: true, at: now };
    expect(entryReviewState(cayman, storage, now)).toBe("awaiting_analyst");
    saveSteps("argus-rpt-a", [step("clear"), step("approve_edd")], storage);
    expect(entryReviewState(cayman, storage, now)).toBe("awaiting_approver");
    const jane = { reportId: "argus-rpt-b", tier: "low", at: now };
    saveSteps("argus-rpt-b", [step("approve")], storage);
    expect(entryReviewState(jane, storage, now)).toBe("decided");
  });
});

describe("acceptedSteps", () => {
  it("lists only the stored steps the rules accept, in order", () => {
    const steps = [step("approve"), step("clear"), step("sign_off"), step("approve_edd")];
    expect(acceptedSteps(steps, CAYMAN)).toEqual([step("clear"), step("approve_edd")]);
  });
});
