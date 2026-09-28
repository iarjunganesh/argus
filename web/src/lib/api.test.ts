import { describe, expect, it, vi } from "vitest";

import {
  API_URL,
  ApiError,
  fetchReport,
  fetchStatus,
  normaliseRequest,
  streamUrl,
  submitAssessment,
} from "./api";

const request = { entity_name: "Acme", entity_type: "corporate", jurisdiction: "NL" } as const;

function answering(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

describe("normaliseRequest", () => {
  it("trims the name and upper-cases the jurisdiction", () => {
    expect(normaliseRequest("  Wirecard AG ", "corporate", " de ")).toEqual({
      entity_name: "Wirecard AG",
      entity_type: "corporate",
      jurisdiction: "DE",
    });
  });

  it.each([
    ["", "corporate", "DE", "Enter the entity's name."],
    ["Acme", "trust", "DE", "Choose the entity type."],
    ["Acme", "individual", "Germany", "two-letter"],
  ])("rejects %j, %j, %j", (name, type, code, message) => {
    const result = normaliseRequest(name, type, code);
    expect("error" in result && result.error).toContain(message);
  });
});

describe("API calls", () => {
  it("submits the assessment with transaction analysis and returns the report ID", async () => {
    const fetcher = answering(200, { report_id: "argus-rpt-1", status: "processing" });
    await expect(submitAssessment(request, fetcher)).resolves.toBe("argus-rpt-1");
    expect(fetcher).toHaveBeenCalledWith(`${API_URL}/api/v1/kyc/assess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...request, include_transaction_analysis: true }),
    });
  });

  it("fails clearly when the API answers without an ID, with an error, or not at all", async () => {
    await expect(submitAssessment(request, answering(200, {}))).rejects.toThrow("report ID");
    await expect(submitAssessment(request, answering(422, {}))).rejects.toThrow("answered 422");
    const down = vi.fn(async (): Promise<Response> => {
      throw new TypeError("Failed to fetch");
    });
    await expect(submitAssessment(request, down)).rejects.toBeInstanceOf(ApiError);
  });

  it("encodes the report ID in every path", async () => {
    const fetcher = answering(200, { status: "completed" });
    await expect(fetchStatus("a/b", fetcher)).resolves.toBe("completed");
    expect(fetcher).toHaveBeenCalledWith(`${API_URL}/api/v1/kyc/status/a%2Fb`, undefined);
    await fetchReport("a/b", fetcher);
    expect(fetcher).toHaveBeenLastCalledWith(`${API_URL}/api/v1/kyc/report/a%2Fb`, undefined);
    expect(streamUrl("a/b")).toBe(`${API_URL}/api/v1/kyc/stream/a%2Fb`);
  });
});
