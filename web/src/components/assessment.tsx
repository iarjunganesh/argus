"use client";

import Link from "next/link";
import { useEffect, useReducer, useState, useSyncExternalStore } from "react";

import { CaseList } from "@/components/case-queue";
import { InvestigationFlow } from "@/components/investigation-flow";
import { ReportView } from "@/components/report-view";
import { API_URL, fetchReport, fetchStatus, streamUrl } from "@/lib/api";
import {
  afterStreamError,
  applyEvent,
  finishedCount,
  initialProgress,
  type ProgressEvent,
} from "@/lib/progress";
import { investigationSummary } from "@/lib/case";
import { demoCaseIndex, forgetReport, recordRun } from "@/lib/queue";
import { AGENTS, type Report } from "@/lib/report";
import { recalledEntityName } from "@/lib/session";

type Outcome = "running" | "completed" | "error" | "not_found" | "unreachable";

const noSubscription = () => () => {};

/** Follow one assessment: its progress stream while it runs, then its report. */
export function Assessment({ reportId }: { reportId: string }) {
  // Read from this tab's storage after hydration; the server render has no name.
  const rememberedName = useSyncExternalStore(
    noSubscription,
    () => recalledEntityName(reportId),
    () => undefined,
  );
  const [progress, dispatch] = useReducer(applyEvent, undefined, initialProgress);
  const [outcome, setOutcome] = useState<Outcome>("running");
  const [report, setReport] = useState<Report>();

  useEffect(() => {
    const source = new EventSource(streamUrl(reportId));
    let unanswered = 0;
    let settled = false;

    const settle = (next: Outcome) => {
      settled = true;
      source.close();
      if (next === "not_found") forgetReport(reportId);
      setOutcome(next);
    };
    const finish = async (status: string) => {
      settled = true;
      source.close();
      try {
        const fetched = await fetchReport(reportId);
        setReport(fetched);
        setOutcome(status === "completed" ? "completed" : "error");
        const index = demoCaseIndex(fetched.entity);
        if (status === "completed" && index !== undefined) {
          recordRun(index, {
            reportId,
            tier: fetched.risk_summary?.overall_risk_tier,
            score: fetched.risk_summary?.overall_risk_score,
            at: Date.now(),
          });
        }
      } catch {
        setOutcome("unreachable");
      }
    };

    const onAgent = (event: MessageEvent<string>) => {
      unanswered = 0;
      dispatch(JSON.parse(event.data) as ProgressEvent);
    };
    source.addEventListener("agent_started", onAgent);
    source.addEventListener("agent_completed", onAgent);
    source.addEventListener("status", (event: MessageEvent<string>) => {
      unanswered = 0;
      const { status } = JSON.parse(event.data) as { status: string };
      // Still processing when the stream reached its time limit: the browser reconnects and
      // resumes after the last event it received.
      if (status !== "processing") void finish(status);
    });
    source.onerror = async () => {
      if (settled) return;
      // The browser reconnects on its own while the API is down, so ask the API directly.
      let status: string | undefined;
      try {
        status = await fetchStatus(reportId);
        unanswered = 0;
      } catch {
        unanswered += 1;
      }
      if (settled) return;
      const action = afterStreamError(status, source.readyState === EventSource.CLOSED, unanswered);
      if (action === "finish") void finish(status ?? "");
      else if (action !== "wait") settle(action);
    };
    return () => {
      settled = true;
      source.close();
    };
  }, [reportId]);

  const finished = finishedCount(progress);
  const name = report?.entity?.name ?? rememberedName;
  const announcement = {
    running: `Assessment running: ${finished} of ${AGENTS.length} agents finished.`,
    completed: "Assessment complete. The report follows.",
    error: "The assessment failed.",
    not_found: "No assessment has this ID.",
    unreachable: "The ARGUS API could not be reached.",
  }[outcome];

  return (
    <div className="grid gap-8 lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="hidden lg:block">
        <CaseList currentReportId={reportId} />
      </aside>
      <div className="min-w-0">
        <h1 className="text-3xl font-semibold tracking-tight">{name || "Assessment"}</h1>
        {report?.entity && (
          <p className="mt-1 text-muted-foreground">
            {report.entity.type === "individual" ? "Individual" : "Company"},{" "}
            {report.entity.jurisdiction}
          </p>
        )}

        <p role="status" aria-live="polite" className="mt-6 font-medium">
          {announcement}
        </p>

        {outcome === "not_found" && (
          <p className="mt-2">
            Check the link, or{" "}
            <Link href="/" className="underline underline-offset-4">
              start a new assessment
            </Link>
            .
          </p>
        )}
        {outcome === "unreachable" && (
          <p className="mt-2 max-w-3xl">
            The API at {API_URL} did not answer. Check that it is running and that its
            ARGUS_CORS_ORIGINS setting lists this site.
          </p>
        )}
        {outcome === "error" && (
          <p role="alert" className="mt-2 max-w-3xl text-destructive">
            {report?.error || "The API recorded an error for this assessment."}
          </p>
        )}

        {outcome === "completed" && report ? (
          <>
            <section aria-labelledby="flow-heading" className="mt-4">
              <details className="rounded-lg border bg-card">
                <summary className="cursor-pointer px-4 py-3 text-sm">
                  <h2 id="flow-heading" className="inline font-medium">
                    Investigation
                  </h2>
                  <span aria-hidden="true">:</span>{" "}
                  <span>
                    {investigationSummary(report.audit_trace, report.total_latency_seconds)}
                  </span>
                </summary>
                <div className="border-t px-4 py-4">
                  <InvestigationFlow progress={progress} />
                </div>
              </details>
            </section>
            <div className="mt-6">
              <ReportView report={report} />
            </div>
          </>
        ) : (
          <section aria-labelledby="flow-heading" className="mt-8">
            <h2 id="flow-heading" className="text-xl font-semibold">
              Investigation
            </h2>
            <div className="mt-4">
              <InvestigationFlow progress={progress} />
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
