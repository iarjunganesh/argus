"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { ApiError, submitAssessment, type AssessmentRequest } from "@/lib/api";
import { rememberEntityName } from "@/lib/session";

/** Shown when the API has not answered after this long: it is probably starting. */
export const COLD_START_AFTER_MS = 3000;
export const COLD_START_NOTICE =
  "Starting the API: it sleeps when nobody is using it, which takes about 20 seconds.";

/** Submit an assessment, then open its page; says so when the API is slow to wake up. */
export function useStartAssessment() {
  const router = useRouter();
  const [error, setError] = useState<string>();
  const [pending, setPending] = useState<string>();
  const [slow, setSlow] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  async function run(request: AssessmentRequest) {
    setError(undefined);
    setSlow(false);
    setPending(request.entity_name);
    timer.current = setTimeout(() => setSlow(true), COLD_START_AFTER_MS);
    try {
      const reportId = await submitAssessment(request);
      rememberEntityName(reportId, request.entity_name);
      router.push(`/assessments/${encodeURIComponent(reportId)}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The assessment could not start.");
      setPending(undefined);
    } finally {
      clearTimeout(timer.current);
      setSlow(false);
    }
  }

  const status = pending
    ? slow
      ? COLD_START_NOTICE
      : `Starting the assessment of ${pending}…`
    : "";
  return { run, pending, error, setError, status };
}
