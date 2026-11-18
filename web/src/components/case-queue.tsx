"use client";

import Link from "next/link";
import { useMemo, useSyncExternalStore } from "react";

import { TierBadge } from "@/components/tier-badge";
import { Button } from "@/components/ui/button";
import type { AssessmentRequest } from "@/lib/api";
import { loadQueue, QUEUE_EVENT, queueRows, rawQueue } from "@/lib/queue";

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  window.addEventListener(QUEUE_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(QUEUE_EVENT, onChange);
  };
}

function useQueueRows() {
  // Read after hydration: the server render has no storage.
  const raw = useSyncExternalStore(
    subscribe,
    () => rawQueue(),
    () => null,
  );
  return useMemo(() => queueRows(raw === null ? {} : loadQueue()), [raw]);
}

const describe = (request: AssessmentRequest) =>
  `${request.entity_type === "corporate" ? "Company" : "Individual"}, ${request.jurisdiction}`;

const assessmentHref = (reportId: string) => `/assessments/${encodeURIComponent(reportId)}`;

/** The demo cases with their last run in this browser, riskiest first. */
export function CaseQueue({
  onRun,
  disabled,
}: {
  onRun: (request: AssessmentRequest) => void;
  disabled?: boolean;
}) {
  const rows = useQueueRows();
  return (
    <div className="mt-6 overflow-hidden rounded-lg border bg-card">
      <ul className="divide-y">
        {rows.map(({ index, request, entry }) => (
          <li key={index} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
            <div className="min-w-0 flex-1">
              <p className="font-medium">{request.entity_name}</p>
              <p className="text-sm text-muted-foreground">{describe(request)}</p>
            </div>
            <div className="flex items-center gap-2 text-sm" data-testid="queue-result">
              {entry ? (
                <>
                  <TierBadge tier={entry.tier} />
                  <span className="tabular-nums">{entry.score ?? "–"}</span>
                </>
              ) : (
                <span className="text-muted-foreground">Not run</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {entry ? (
                <Link
                  href={assessmentHref(entry.reportId)}
                  aria-label={`Open the assessment of ${request.entity_name}`}
                  className="rounded-md px-2 py-1 text-sm font-medium underline underline-offset-4 focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none"
                >
                  Open
                </Link>
              ) : null}
              <Button
                variant="outline"
                disabled={disabled}
                onClick={() => onRun(request)}
                aria-label={`Run the assessment of ${request.entity_name}`}
              >
                Run
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The same cases as a narrow list beside an open case. */
export function CaseList({ currentReportId }: { currentReportId?: string }) {
  const rows = useQueueRows();
  return (
    <nav aria-label="Cases" className="rounded-lg border bg-card">
      <p className="border-b px-3 py-2 text-sm font-semibold">Cases</p>
      <ul className="divide-y text-sm">
        {rows.map(({ index, request, entry }) => {
          const current = entry?.reportId === currentReportId;
          const label = (
            <>
              <span className="block truncate font-medium">{request.entity_name}</span>
              <span className="mt-0.5 flex items-center gap-2 text-muted-foreground">
                {entry ? <TierBadge tier={entry.tier} /> : "Not run"}
              </span>
            </>
          );
          return (
            <li key={index}>
              {entry ? (
                <Link
                  href={assessmentHref(entry.reportId)}
                  aria-current={current ? "page" : undefined}
                  className={`block px-3 py-2 focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none ${current ? "bg-muted" : "hover:bg-muted"}`}
                >
                  {label}
                </Link>
              ) : (
                <div className="px-3 py-2">{label}</div>
              )}
            </li>
          );
        })}
      </ul>
      <p className="border-t px-3 py-2 text-xs text-muted-foreground">
        Runs are kept in this browser for 24 hours.
      </p>
    </nav>
  );
}
