import { describe, expect, it } from "vitest";

import {
  barPercent,
  citationParts,
  eddLabel,
  evidenceSummary,
  explanationSourceLabel,
  NOT_REPORTED,
  sanctionsLabel,
  sourceLabel,
  tierBasisLabel,
  tierTone,
} from "./report";

describe("labels", () => {
  it("words each known value and says when a value is missing", () => {
    expect(tierBasisLabel("sanctions_match")).toBe("Sanctions hold");
    expect(tierBasisLabel("score")).toBe("Score band");
    expect(tierBasisLabel()).toBe(NOT_REPORTED);
    expect(sanctionsLabel("potential_match")).toBe("Potential match");
    expect(sanctionsLabel("something_new")).toBe(NOT_REPORTED);
    expect(eddLabel(true)).toBe("Required");
    expect(eddLabel(false)).toBe("Not required by a rule");
    expect(eddLabel(undefined)).toBe(NOT_REPORTED);
    expect(sourceLabel("demo_profile")).toBe("Recorded demo profile");
    expect(sourceLabel("unavailable")).toBe("Agent unavailable");
    expect(sourceLabel(null)).toBe(NOT_REPORTED);
    expect(explanationSourceLabel("model")).toMatch(/language model/);
    expect(explanationSourceLabel("fallback")).toMatch(/template/);
  });
});

describe("tierTone", () => {
  it.each([
    ["LOW", "low"],
    ["MEDIUM", "medium"],
    ["HIGH", "high"],
    ["CRITICAL", "critical"],
    ["UNKNOWN", "unknown"],
    [undefined, "unknown"],
  ])("%s is %s", (tier, tone) => {
    expect(tierTone(tier)).toBe(tone);
  });
});

describe("barPercent", () => {
  it("clamps the score to a bar width", () => {
    expect(barPercent(120)).toBe(100);
    expect(barPercent(-5)).toBe(0);
    expect(barPercent(42.5)).toBe(42.5);
    expect(barPercent(undefined)).toBe(0);
    expect(barPercent(Number.NaN)).toBe(0);
  });
});

describe("evidenceSummary", () => {
  it("says the knowledge bases answered when they did and nothing fell back", () => {
    expect(evidenceSummary({ retrieval_queries: 3, data_backend: "azure" })).toEqual({
      grounded: true,
      text: "Knowledge bases answered 3 searches (azure data)",
    });
    expect(evidenceSummary({ retrieval_queries: 1, data_backend: "local" }).text).toBe(
      "Knowledge bases answered 1 search (local data)",
    );
  });

  it("names every tool that fell back, even when searches answered", () => {
    expect(
      evidenceSummary({
        retrieval_queries: 1,
        fallbacks: { identity: ["ocr_processor[0]"], screening: [] },
      }),
    ).toEqual({ grounded: false, text: "Fallback used: identity (ocr_processor[0])" });
  });

  it("says when no search answered", () => {
    expect(evidenceSummary({ retrieval_queries: 0 })).toEqual({
      grounded: false,
      text: "No knowledge-base search answered",
    });
    expect(evidenceSummary().grounded).toBe(false);
  });
});

describe("citationParts", () => {
  it("keeps only the parts that are present", () => {
    expect(citationParts({ document: "fatf.pdf", article: "Rec. 12" })).toEqual([
      { label: "Document", value: "fatf.pdf" },
      { label: "Article", value: "Rec. 12" },
    ]);
    expect(citationParts(null)).toEqual([]);
  });
});
