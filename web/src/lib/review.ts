// The demo review's rules: who may take which step, in which order, for which case. Nothing here
// is sent anywhere; the steps are kept in this browser (review-store.ts).

export type MatchAction = "confirm" | "clear" | "escalate_match";
export type CaseAction = "approve" | "approve_edd" | "decline" | "escalate";
export type ApproverAction = "sign_off" | "return";
export type ReviewAction = MatchAction | CaseAction | ApproverAction;
