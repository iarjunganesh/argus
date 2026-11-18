import { evidenceFields, findingTitle, formatTime, uncertaintyLabel } from "@/lib/case";
import { sourceLabel, type EvidenceRecord, type Finding } from "@/lib/report";

const UNCERTAINTY_STYLE: Record<Finding["uncertainty"], string> = {
  potential: "bg-caution text-caution-foreground",
  unknown: "bg-muted text-foreground",
  observed: "bg-secondary text-secondary-foreground",
};

/** One finding: what it says, how certain it is, where it came from, and its evidence. */
export function FindingItem({
  finding,
  evidence,
}: {
  finding: Finding;
  evidence: Record<string, EvidenceRecord>;
}) {
  const records = finding.evidence_refs
    .map((ref) => evidence[ref])
    .filter((record): record is EvidenceRecord => Boolean(record));
  return (
    <li className="rounded-lg border bg-background px-4 py-3" data-finding={finding.kind}>
      <p className="font-medium">{findingTitle(finding)}</p>
      <p className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
        <span
          data-uncertainty={finding.uncertainty}
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${UNCERTAINTY_STYLE[finding.uncertainty]}`}
        >
          {uncertaintyLabel(finding.uncertainty)}
        </span>
        <span>{sourceLabel(finding.source)}</span>
        <span>Observed {formatTime(finding.observed_at)}</span>
      </p>
      {records.length ? (
        <details className="mt-2">
          <summary className="cursor-pointer text-sm font-medium underline-offset-4 hover:underline">
            Evidence ({records.length})
          </summary>
          <div className="mt-2 grid gap-3">
            {records.map((record) => (
              <div key={record.id} className="rounded-md border bg-card px-3 py-2">
                <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-1 text-sm">
                  <dt className="text-muted-foreground">Source</dt>
                  <dd>{sourceLabel(record.source)}</dd>
                  {evidenceFields(record).map((field) => (
                    <div key={field.label} className="contents">
                      <dt className="text-muted-foreground">{field.label}</dt>
                      <dd className="break-words">{field.value}</dd>
                    </div>
                  ))}
                </dl>
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-muted-foreground">
                    Raw record
                  </summary>
                  {/* Wrapped, not scrolled: a scrolling box would need keyboard focus. */}
                  <pre className="mt-1 font-mono text-xs leading-relaxed whitespace-pre-wrap [overflow-wrap:anywhere]">
                    {JSON.stringify(record, null, 2)}
                  </pre>
                </details>
              </div>
            ))}
          </div>
        </details>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">No evidence record was attached.</p>
      )}
    </li>
  );
}
