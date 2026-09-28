// The ARGUS API, called from the browser. The API must list this site's origin in
// ARGUS_CORS_ORIGINS.

import type { Report } from "./report";

/** Set at build time. Defaults to a local API. */
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(
  /\/+$/,
  "",
);

export type EntityType = "individual" | "corporate";

export interface AssessmentRequest {
  entity_name: string;
  entity_type: EntityType;
  jurisdiction: string;
}

export class ApiError extends Error {}

async function call<T>(
  path: string,
  init?: RequestInit,
  fetcher: typeof fetch = fetch,
): Promise<T> {
  let response: Response;
  try {
    response = await fetcher(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(`The ARGUS API at ${API_URL} could not be reached.`);
  }
  if (!response.ok) {
    throw new ApiError(`The ARGUS API answered ${response.status} for ${path}.`);
  }
  return (await response.json()) as T;
}

/** Submit an assessment and return its report ID; the assessment runs on in the API. */
export async function submitAssessment(
  request: AssessmentRequest,
  fetcher: typeof fetch = fetch,
): Promise<string> {
  const body = await call<{ report_id?: string }>(
    "/api/v1/kyc/assess",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...request, include_transaction_analysis: true }),
    },
    fetcher,
  );
  if (!body.report_id) throw new ApiError("The ARGUS API did not return a report ID.");
  return body.report_id;
}

export function fetchReport(reportId: string, fetcher: typeof fetch = fetch): Promise<Report> {
  return call<Report>(`/api/v1/kyc/report/${encodeURIComponent(reportId)}`, undefined, fetcher);
}

export async function fetchStatus(
  reportId: string,
  fetcher: typeof fetch = fetch,
): Promise<string> {
  const path = `/api/v1/kyc/status/${encodeURIComponent(reportId)}`;
  return (await call<{ status: string }>(path, undefined, fetcher)).status;
}

export function streamUrl(reportId: string): string {
  return `${API_URL}/api/v1/kyc/stream/${encodeURIComponent(reportId)}`;
}

/** The request as the form sends it: trimmed name, upper-case jurisdiction. */
export function normaliseRequest(
  name: string,
  type: string,
  jurisdiction: string,
): AssessmentRequest | { error: string } {
  const entity_name = name.trim();
  const code = jurisdiction.trim().toUpperCase();
  if (!entity_name) return { error: "Enter the entity's name." };
  if (type !== "individual" && type !== "corporate") return { error: "Choose the entity type." };
  if (!/^[A-Z]{2}$/.test(code)) {
    return { error: "Enter the jurisdiction as a two-letter country code, such as DE." };
  }
  return { entity_name, entity_type: type, jurisdiction: code };
}
