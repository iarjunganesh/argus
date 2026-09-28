"use client";

import Link from "next/link";
import { useEffect, useReducer, useState } from "react";

import { InvestigationFlow } from "@/components/investigation-flow";
import { ReportView } from "@/components/report-view";
import { API_URL, fetchReport, fetchStatus, streamUrl } from "@/lib/api";
import { AGENTS, type Report } from "@/lib/report";
import { applyEvent, finishedCount, initialProgress, type ProgressEvent } from "@/lib/progress";

type Outcome = "running" | "completed" | "error" | "not_found" | "unreachable";

/** Follow one assessment: its progress stream while it runs, then its report. */
export function Assessment({ reportId, entityName }: { reportId: string; entityName?: string }) {
  const [progress, dispatch] = useReducer(applyEvent, undefined, initialProgress);
  const [outcome, setOutcome] = useState<Outcome>("running");
  const [report, setReport] = useState<Report>();

  useEffect(() => {
    const source = new EventSource(streamUrl(reportId));
    const onAgent = (event: MessageEvent<string>) =>
      dispatch(JSON.parse(event.data) as ProgressEvent);
    source.addEventListener("agent_started", onAgent);
    source.addEventListener("agent_completed", onAgent);
    source.addEventListener("status", async (event: MessageEvent<string>) => {
      const { status } = JSON.parse(event.data) as { status: string };
      // Still processing when the stream reached its time limit: the browser reconnects and
      // resumes after the last event it received.
      if (status === "processing") return;
      source.close();
      try {
        setReport(await fetchReport(reportId));
        setOutcome(status === "completed" ? "completed" : "error");
      } catch {
        setOutcome("unreachable");
      }
    });
    source.onerror = async () => {
      // While the browser is reconnecting on its own, readyState is CONNECTING; CLOSED means
      // it gave up (the API refused the stream or could not be reached).
      if (source.readyState !== EventSource.CLOSED) return;
      try {
        setOutcome((await fetchStatus(reportId)) === "not_found" ? "not_found" : "unreachable");
      } catch {
        setOutcome("unreachable");
      }
    };
    return () => source.close();
  }, [reportId]);

  const finished = finishedCount(progress);
  const name = report?.entity?.name ?? entityName;
  const announcement = {
    running: `Assessment running: ${finished} of ${AGENTS.length} agents finished.`,
    completed: "Assessment complete. The report follows.",
    error: "The assessment failed.",
    not_found: "No assessment has this ID.",
    unreachable: "The ARGUS API could not be reached.",
  }[outcome];

  return (
    <div>
      <p className="text-sm text-muted-foreground">Assessment {reportId}</p>
      <h1 className="mt-1 text-3xl font-semibold tracking-tight">{name || "Assessment"}</h1>
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

      <section aria-labelledby="flow-heading" className="mt-8">
        <h2 id="flow-heading" className="text-xl font-semibold">
          Investigation
        </h2>
        <div className="mt-4">
          <InvestigationFlow progress={progress} />
        </div>
      </section>

      {outcome === "completed" && report && (
        <div className="mt-12">
          <ReportView report={report} />
        </div>
      )}
    </div>
  );
}
