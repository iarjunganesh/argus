import { CircleAlert, CircleCheck } from "lucide-react";
import type { ReactNode } from "react";

import { TierBadge } from "@/components/tier-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AGENTS,
  barPercent,
  citationParts,
  DIMENSIONS,
  eddLabel,
  evidenceSummary,
  explanationSourceLabel,
  NOT_REPORTED,
  sanctionsLabel,
  sourceLabel,
  tierBasisLabel,
  tierTone,
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

function Facts({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-6 gap-y-1.5 text-sm">
      {items.map(([term, value]) => (
        <div key={term} className="contents">
          <dt className="text-muted-foreground">{term}</dt>
          <dd className="font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function List({ items, empty }: { items?: string[]; empty: string }) {
  if (!items?.length) return <p className="text-muted-foreground">{empty}</p>;
  return (
    <ul className="grid max-w-3xl list-disc gap-1.5 pl-5">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

const BAR = {
  low: "bg-risk-low",
  medium: "bg-risk-medium",
  high: "bg-risk-high",
  critical: "bg-risk-critical",
  unknown: "bg-risk-unknown",
} as const;

function Decision({ report }: { report: Report }) {
  const summary = report.risk_summary ?? {};
  const score = summary.overall_risk_score;
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
      <p className="mt-6 max-w-3xl text-lg">
        {summary.decision_recommendation || "No recommendation was recorded."}
      </p>
      <h3 className="mt-6 font-semibold">Why this rating</h3>
      <div className="mt-2">
        <List items={report.key_findings} empty="No material findings were recorded." />
      </div>
    </section>
  );
}

function Evidence({ report }: { report: Report }) {
  const trace = report.audit_trace ?? {};
  const evidence = evidenceSummary(trace);
  const Icon = evidence.grounded ? CircleCheck : CircleAlert;
  return (
    <div className="mt-6 grid gap-4">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {(
          [
            ["Agents that ran", trace.agents_invoked?.length ?? NOT_REPORTED],
            ["Data", trace.data_backend ?? NOT_REPORTED],
            ["Knowledge-base searches", trace.retrieval_queries ?? NOT_REPORTED],
            [
              "Run time",
              report.total_latency_seconds !== undefined
                ? `${report.total_latency_seconds} s`
                : NOT_REPORTED,
            ],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded-lg border bg-card px-4 py-3">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="text-lg font-semibold tabular-nums">{value}</p>
          </div>
        ))}
      </div>
      <p
        data-grounded={evidence.grounded}
        className={
          evidence.grounded
            ? "flex items-center gap-2 rounded-lg bg-grounded px-4 py-2 text-sm font-medium text-grounded-foreground"
            : "flex items-center gap-2 rounded-lg bg-caution px-4 py-2 text-sm font-medium text-caution-foreground"
        }
      >
        <Icon aria-hidden className="size-4 shrink-0" />
        {evidence.text}
      </p>
    </div>
  );
}

function Dimensions({ report }: { report: Report }) {
  const scores = report.dimension_scores ?? {};
  return (
    <Table label="Risk dimensions">
      <TableHeader>
        <TableRow>
          <TableHead>Dimension</TableHead>
          <TableHead>Weight</TableHead>
          <TableHead className="w-2/5">Score</TableHead>
          <TableHead>Tier</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {DIMENSIONS.map(({ key, label }) => {
          const dimension = scores[key] ?? {};
          return (
            <TableRow key={key}>
              <TableCell className="font-medium">{label}</TableCell>
              <TableCell className="tabular-nums">{dimension.weight ?? "–"}</TableCell>
              <TableCell>
                <div className="flex items-center gap-3">
                  <span className="w-10 text-right tabular-nums">{dimension.score ?? "–"}</span>
                  <span aria-hidden className="hidden h-2 flex-1 rounded-full bg-muted sm:block">
                    <span
                      className={`block h-2 rounded-full ${BAR[tierTone(dimension.tier)]}`}
                      style={{ width: `${barPercent(dimension.score)}%` }}
                    />
                  </span>
                </div>
              </TableCell>
              <TableCell>
                <TierBadge tier={dimension.tier} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

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

function AuditTrail({ report }: { report: Report }) {
  const trace = report.audit_trace ?? {};
  const fallbacks = trace.fallbacks ?? {};
  return (
    <div className="grid gap-6">
      <Facts
        items={[
          ["Report ID", report.report_id ?? NOT_REPORTED],
          ["Task ID", trace.task_id ?? NOT_REPORTED],
          ["Generated at", report.generated_at ?? NOT_REPORTED],
          ["Explanation", explanationSourceLabel(report.explanation_source)],
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
              <TableCell>{trace[`${id}_status`] ?? NOT_REPORTED}</TableCell>
              <TableCell>{sourceLabel(trace.agent_sources?.[id])}</TableCell>
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
    </div>
  );
}

/** The finished report: decision first, then the evidence behind it. */
export function ReportView({ report }: { report: Report }) {
  return (
    <div>
      <Decision report={report} />
      <Evidence report={report} />
      <Section id="dimensions-heading" title="Risk dimensions">
        <Dimensions report={report} />
      </Section>
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
        <List items={report.recommended_actions} empty="No actions were recommended." />
      </Section>
      <Section id="audit-heading" title="Audit trail">
        <AuditTrail report={report} />
      </Section>
      <details className="mt-10 rounded-lg border bg-card">
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
