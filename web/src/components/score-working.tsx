import { FindingItem } from "@/components/finding-item";
import { TierBadge } from "@/components/tier-badge";
import { checkLabel, groupFindings, isSanctionsHold, scoreWorking } from "@/lib/case";
import type { Report } from "@/lib/report";

const percent = (weight?: number) =>
  weight === undefined ? "–" : `${Math.round(weight * 1000) / 10}%`;

const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** The score's working: each dimension's points, and behind each its findings and evidence. */
export function ScoreWorking({ report }: { report: Report }) {
  const { rows, total } = scoreWorking(report.dimension_scores);
  const { byDimension, checksCompleted } = groupFindings(report.findings);
  const obligations = report.decision_record?.obligations ?? [];
  const evidence = report.evidence ?? {};
  return (
    <section aria-labelledby="working-heading" className="mt-10">
      <h2 id="working-heading" className="text-xl font-semibold">
        Why this score
      </h2>
      <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
        Each dimension&apos;s score times its weight; the points add up to the overall score. Open a
        dimension for its findings and their evidence.
      </p>
      <div className="mt-4 divide-y rounded-lg border bg-card">
        {rows.map((row) => {
          const findings = byDimension[row.key];
          const checks = checksCompleted[row.key];
          const regulatory = row.key === "regulatory";
          return (
            <details key={row.key} data-dimension={row.key} className="px-4 py-3">
              <summary className="flex cursor-pointer flex-wrap items-center gap-x-4 gap-y-2">
                <span className="w-44 font-medium">{row.label}</span>
                <span className="text-sm tabular-nums">
                  {row.score ?? "–"} × {percent(row.weight)} ={" "}
                  <span className="font-semibold">{row.points ?? "–"}</span>
                </span>
                <TierBadge tier={row.tier} />
                <span className="text-sm text-muted-foreground sm:ml-auto">
                  {regulatory
                    ? count(obligations.length, "obligation", "obligations")
                    : count(findings.length, "finding", "findings")}
                </span>
              </summary>
              <div className="mt-3 grid gap-3">
                {checks.length ? (
                  <p className="text-sm text-muted-foreground">
                    Checks completed: {checks.map(checkLabel).join(", ")}
                  </p>
                ) : null}
                {regulatory ? (
                  obligations.length ? (
                    <ul className="grid max-w-3xl list-disc gap-1.5 pl-5 text-sm">
                      {obligations.map((obligation) => (
                        <li key={obligation}>{obligation}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">No obligation was recorded.</p>
                  )
                ) : findings.length ? (
                  <ul className="grid gap-2">
                    {findings.map((finding) => (
                      <FindingItem key={finding.id} finding={finding} evidence={evidence} />
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No finding was recorded.</p>
                )}
              </div>
            </details>
          );
        })}
        <p className="flex flex-wrap items-baseline gap-x-2 px-4 py-3">
          <span className="w-44 font-semibold">Total</span>
          <span className="text-lg font-semibold tabular-nums" data-testid="working-total">
            {total ?? "–"}
          </span>
          <span className="text-sm text-muted-foreground">of 100</span>
        </p>
      </div>
      {isSanctionsHold(report) ? (
        <p className="mt-3 text-sm font-medium">
          The sanctions hold, not the score band, sets the tier.
        </p>
      ) : null}
    </section>
  );
}
