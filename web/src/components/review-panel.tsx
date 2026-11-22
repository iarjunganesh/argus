"use client";

import { useId, useState, type FormEvent } from "react";

import { useReview, type Review } from "@/components/use-review";
import { Button } from "@/components/ui/button";
import { formatTime } from "@/lib/case";
import type { Report } from "@/lib/report";
import {
  ACTION_LABELS,
  isMatchAction,
  ROLE_LABELS,
  STATE_LABELS,
  type ReviewAction,
} from "@/lib/review";
import type { Role, Step } from "@/lib/review-store";

export const DEMO_LABEL =
  "Demo review: kept in this browser only and sent nowhere. ARGUS recommends; a person decides.";

const NOT_KEPT =
  "Not kept: this browser's storage is blocked or full, so the review lasts only while this page is open.";

/** The review's steps so far: what was chosen, by which role, when and why. */
export function ReviewSteps({ steps, empty }: { steps: Step[]; empty: string }) {
  if (!steps.length) return <p className="text-sm text-muted-foreground">{empty}</p>;
  return (
    <ol className="grid gap-2 text-sm">
      {steps.map((step, index) => (
        <li key={index} className="rounded-lg border px-3 py-2">
          <p>
            <span className="font-medium">{ACTION_LABELS[step.action]}</span>
            <span className="text-muted-foreground">
              {" "}
              · {ROLE_LABELS[step.reviewer]} ·{" "}
              <time dateTime={step.decided_at}>{formatTime(step.decided_at)}</time>
            </span>
          </p>
          {step.rationale ? <p className="mt-1 break-words">{step.rationale}</p> : null}
        </li>
      ))}
    </ol>
  );
}

function StepForm({
  legend,
  actions,
  add,
}: {
  legend: string;
  actions: ReviewAction[];
  add: Review["add"];
}) {
  const id = useId();
  const [action, setAction] = useState<ReviewAction>();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string>();
  const optional = action === "sign_off";

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const problem = action ? add(action, reason) : "Choose a step.";
    setError(problem);
    if (!problem) {
      setAction(undefined);
      setReason("");
    }
  };

  return (
    <form onSubmit={submit} noValidate className="mt-4 grid max-w-xl gap-4">
      <fieldset>
        <legend className="font-medium">{legend}</legend>
        <div className="mt-2 grid gap-2">
          {actions.map((option) => (
            <label key={option} className="flex items-center gap-2">
              <input
                type="radio"
                name={`${id}-action`}
                value={option}
                checked={action === option}
                onChange={() => setAction(option)}
                className="size-4 accent-primary"
              />
              {ACTION_LABELS[option]}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-1.5">
        <label htmlFor={`${id}-reason`} className="font-medium">
          {optional ? "Comment (optional)" : "Reason"}
        </label>
        <textarea
          id={`${id}-reason`}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          rows={3}
          aria-required={optional ? undefined : true}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          className="w-full rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-base outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive md:text-sm dark:bg-input/30"
        />
      </div>
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      <div>
        <Button type="submit" size="lg" className="h-10 px-4">
          Record the step
        </Button>
      </div>
    </form>
  );
}

const waitingFor = (by: Role) =>
  by === "approver"
    ? "Waiting for the approver. Switch the role to Approver to sign off or return the case."
    : "Waiting for the analyst. Switch the role to Analyst to take the next step.";

function Notes({ kept }: { kept: boolean }) {
  return (
    <div className="mt-4 grid gap-1 text-sm text-muted-foreground">
      <p>{DEMO_LABEL}</p>
      <p>The demo cannot check that the analyst and the approver are two people.</p>
      {kept ? null : <p className="font-medium text-foreground">{NOT_KEPT}</p>}
    </div>
  );
}

function MatchReview({ review }: { review: Review }) {
  const { steps, allowed, by, role, add } = review;
  const open = allowed.filter(isMatchAction);
  const resolved = steps.filter((step) => isMatchAction(step.action));
  return (
    <div className="mt-6 border-t pt-4">
      <h3 className="font-semibold">Resolve the match</h3>
      {/* Always rendered, so a step recorded here is announced when its form disappears. */}
      <div aria-live="polite">
        {resolved.length ? <ReviewSteps steps={resolved} empty="" /> : null}
      </div>
      {open.length && by ? (
        role === by ? (
          <StepForm key={open.join()} legend="Is this the listed party?" actions={open} add={add} />
        ) : (
          <p className="mt-2 text-sm">{waitingFor(by)}</p>
        )
      ) : null}
      <Notes kept={review.kept} />
    </div>
  );
}

function CaseReview({ review }: { review: Review }) {
  const { steps, state, allowed, by, role, add } = review;
  const open = allowed.filter((action) => !isMatchAction(action));
  const matchFirst = allowed.some(isMatchAction);
  const legend = by === "approver" ? "Sign off the analyst's decision?" : "Decide the case";
  return (
    <section
      id="review"
      aria-labelledby="review-heading"
      className="mt-10 scroll-mt-6 rounded-xl border bg-card p-6"
    >
      <h2 id="review-heading" className="text-xl font-semibold">
        Review
      </h2>
      <p aria-live="polite" className="mt-1">
        State: <span className="font-medium">{STATE_LABELS[state]}</span>
      </p>
      {matchFirst ? (
        <p className="mt-2 text-sm">
          Resolve the{" "}
          <a href="#match" className="underline underline-offset-4">
            potential sanctions match
          </a>{" "}
          first.
        </p>
      ) : null}
      {open.length && by ? (
        role === by ? (
          <StepForm key={open.join()} legend={legend} actions={open} add={add} />
        ) : (
          <p className="mt-2 text-sm">{waitingFor(by)}</p>
        )
      ) : null}
      <h3 className="mt-6 mb-2 font-semibold">Steps so far</h3>
      <div aria-live="polite">
        <ReviewSteps steps={steps} empty="No step recorded yet." />
      </div>
      <Notes kept={review.kept} />
    </section>
  );
}

/** Where a person records the decision: the match (inside the match panel) or the case. */
export function ReviewPanel({ report, scope }: { report: Report; scope: "match" | "case" }) {
  const review = useReview(report);
  return scope === "match" ? <MatchReview review={review} /> : <CaseReview review={review} />;
}

/** The review's state for the case header. */
export function ReviewStatus({ report }: { report: Report }) {
  const { state } = useReview(report);
  return (
    <div className="grid gap-0.5">
      <p className="text-foreground">
        Review: <span className="font-medium">{STATE_LABELS[state]}</span>
      </p>
      <p>{DEMO_LABEL}</p>
    </div>
  );
}

/** The review's steps for the audit trail. */
export function ReviewAudit({ report }: { report: Report }) {
  const { steps } = useReview(report);
  return (
    <section aria-labelledby="review-audit-heading">
      <h3 id="review-audit-heading" className="mb-2 font-semibold">
        Review steps (this browser only)
      </h3>
      <ReviewSteps steps={steps} empty="No review step recorded in this browser." />
    </section>
  );
}
