import type { ReactNode } from "react";

import { CaseHeader } from "@/components/case-header";
import { Facts } from "@/components/facts";
import { MatchPanel } from "@/components/match-panel";
import { ReviewAudit, ReviewPanel, ReviewStatus } from "@/components/review-panel";
import { ScoreWorking } from "@/components/score-working";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { actionsBesidesObligations, formatTime, isSanctionsHold } from "@/lib/case";
import {
  AGENTS,
  citationParts,
  evidenceSummary,
  explanationSourceLabel,
  NOT_REPORTED,
  sourceLabel,
  type Report,
} from "@/lib/report";

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="mt-10">
      <h2 id={id} className="text-xl font-semibold">
        {title}
      </h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function List({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) return <p className="text-muted-foreground">{empty}</p>;
  return (
    <ul className="grid max-w-3xl list-disc gap-1.5 pl-5">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

const capitalised = (value?: string) =>
  value ? value.charAt(0).toUpperCase() + value.slice(1) : NOT_REPORTED;

function Triggers({ report }: { report: Report }) {
  const triggers = report.regulatory_triggers ?? [];
  if (!triggers.length) {
    return <p className="text-muted-foreground">No regulation was cited for this case.</p>;
  }
  return (
    <ul className="grid gap-3">
      {triggers.map((trigger, index) => {
        const parts = citationParts(trigger.citation);
        return (
          <li key={index} className="rounded-lg border bg-card px-4 py-3">
            <p className="max-w-3xl">{trigger.rule}</p>
            {parts.length ? (
              <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm">
                {parts.map((part) => (
                  <div key={part.label}>
                    <dt className="inline text-muted-foreground">{part.label}: </dt>
                    <dd className="inline">{part.value}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">No citation</p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function AuditTrail({ report, extra }: { report: Report; extra?: ReactNode }) {
  const trace = report.audit_trace ?? {};
  const fallbacks = trace.fallbacks ?? {};
  return (
    <details className="mt-10 rounded-lg border bg-card">
      <summary className="cursor-pointer px-4 py-3">
        <h2 id="audit-heading" className="inline text-xl font-semibold">
          Audit trail
        </h2>
      </summary>
      <div className="grid gap-6 border-t px-4 py-4">
        <Facts
          items={[
            ["Report ID", report.report_id ?? NOT_REPORTED],
            ["Task ID", trace.task_id ?? NOT_REPORTED],
            ["Generated", formatTime(report.generated_at)],
            ["Explanation", explanationSourceLabel(report.explanation_source)],
            ["Data", trace.data_backend ?? NOT_REPORTED],
            ["Knowledge bases", evidenceSummary(trace).text],
            [
              "Run time",
              report.total_latency_seconds !== undefined
                ? `${report.total_latency_seconds} s`
                : NOT_REPORTED,
            ],
          ]}
        />
        <Table label="Agent results">
          <TableHeader>
            <TableRow>
              <TableHead>Agent</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Result</TableHead>
              <TableHead>Tools that fell back</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {AGENTS.map(({ id, name }) => (
              <TableRow key={id}>
                <TableCell className="font-medium">{name}</TableCell>
                <TableCell>{capitalised(trace[`${id}_status`])}</TableCell>
                <TableCell className="whitespace-normal">
                  {sourceLabel(trace.agent_sources?.[id])}
                </TableCell>
                <TableCell>{fallbacks[id]?.join(", ") || "None"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {report.timeline?.length ? (
          <ol className="grid gap-1 text-sm">
            {report.timeline.map((step, index) => (
              <li key={index} className="flex gap-4">
                <span className="w-20 text-muted-foreground tabular-nums">{step.time}</span>
                <span>{step.step}</span>
              </li>
            ))}
          </ol>
        ) : null}
        {extra}
      </div>
    </details>
  );
}

/** The finished report as a case file: the decision and what blocks it first, then the why. */
export function ReportView({ report, auditExtra }: { report: Report; auditExtra?: ReactNode }) {
  const hold = isSanctionsHold(report);
  const actions = actionsBesidesObligations(
    report.recommended_actions,
    report.decision_record?.obligations,
  );
  const recommendation = report.risk_summary?.decision_recommendation;
  // The demo review needs a report to key it by and a tier for its rules.
  const reviewable = Boolean(report.report_id && report.risk_summary?.overall_risk_tier);
  return (
    <div>
      <CaseHeader
        report={report}
        reviewSlot={reviewable ? <ReviewStatus report={report} /> : undefined}
      />
      <MatchPanel report={report}>
        {reviewable ? <ReviewPanel report={report} scope="match" /> : null}
      </MatchPanel>
      <ScoreWorking report={report} />
      {reviewable ? <ReviewPanel report={report} scope="case" /> : null}
      <Section id="explanation-heading" title="Explanation">
        <p className="text-sm text-muted-foreground">
          Analyst view. {explanationSourceLabel(report.explanation_source)}.
        </p>
        <p className="mt-2 max-w-3xl text-lg leading-relaxed">
          {report.explanation || "No explanation was recorded."}
        </p>
      </Section>
      <Section id="triggers-heading" title="Regulations cited">
        <Triggers report={report} />
      </Section>
      <Section id="actions-heading" title="Recommended actions">
        <List
          items={hold && recommendation ? [recommendation, ...actions] : actions}
          empty="No actions were recommended."
        />
      </Section>
      <AuditTrail
        report={report}
        extra={
          <>
            {reviewable ? <ReviewAudit report={report} /> : null}
            {auditExtra}
          </>
        }
      />
      <details className="mt-4 rounded-lg border bg-card">
        <summary className="cursor-pointer px-4 py-3 font-medium">Full report as JSON</summary>
        <pre
          tabIndex={0}
          className="max-h-[32rem] overflow-auto border-t px-4 py-3 font-mono text-xs leading-relaxed whitespace-pre-wrap"
        >
          {JSON.stringify(report, null, 2)}
        </pre>
      </details>
    </div>
  );
}
