import { AlertOctagon } from "lucide-react";
import type { ReactNode } from "react";

import { Facts } from "@/components/facts";
import { TierBadge } from "@/components/tier-badge";
import { buttonVariants } from "@/components/ui/button";
import { isSanctionsHold } from "@/lib/case";
import { eddLabel, sanctionsLabel, tierBasisLabel, type Report } from "@/lib/report";

/** The top of the case: tier, score, what sets the tier, what blocks the case, the next step. */
export function CaseHeader({ report, reviewSlot }: { report: Report; reviewSlot?: ReactNode }) {
  const summary = report.risk_summary ?? {};
  const score = summary.overall_risk_score;
  const hold = isSanctionsHold(report);
  const recommendation = summary.decision_recommendation || "No recommendation was recorded.";
  return (
    <section aria-labelledby="decision-heading" className="rounded-xl border bg-card p-6">
      <h2 id="decision-heading" className="text-sm font-medium text-muted-foreground">
        Recommendation for the reviewer
      </h2>
      <div className="mt-3 flex flex-wrap items-end gap-x-10 gap-y-4">
        <div>
          <p className="text-sm text-muted-foreground">Risk tier</p>
          <p className="mt-1" data-testid="risk-tier">
            <TierBadge tier={summary.overall_risk_tier} className="px-3 py-1 text-3xl" />
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Risk score</p>
          <p className="mt-1 text-4xl font-semibold tabular-nums">
            <span data-testid="risk-score">{score ?? "–"}</span>
            <span className="text-base font-normal text-muted-foreground"> of 100</span>
          </p>
        </div>
        <Facts
          items={[
            ["Tier set by", tierBasisLabel(summary.tier_basis)],
            ["Sanctions screening", sanctionsLabel(summary.sanctions_screening)],
            ["Enhanced due diligence", eddLabel(summary.edd_required)],
          ]}
        />
      </div>
      {hold ? (
        <div
          role="note"
          className="mt-6 flex max-w-3xl gap-3 rounded-lg bg-caution px-4 py-3 text-caution-foreground"
        >
          <AlertOctagon aria-hidden className="mt-1 size-5 shrink-0" />
          <p className="text-lg font-medium">{recommendation}</p>
        </div>
      ) : (
        <p className="mt-6 max-w-3xl text-lg">{recommendation}</p>
      )}
      <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-3">
        <a
          href={hold ? "#match" : "#working-heading"}
          className={buttonVariants({ size: "lg", className: "h-10 px-4" })}
        >
          {hold ? "Review the match" : "Review the findings"}
        </a>
        <div className="text-sm text-muted-foreground">
          {reviewSlot ?? "A person decides; this demo does not record the decision yet."}
        </div>
      </div>
    </section>
  );
}
