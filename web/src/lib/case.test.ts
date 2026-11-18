import { describe, expect, it } from "vitest";

import {
  actionsBesidesObligations,
  checkLabel,
  findingTitle,
  formatTime,
  groupFindings,
  investigationSummary,
  isSanctionsHold,
  sanctionsListing,
  scoreWorking,
  uncertaintyLabel,
} from "./case";
import { NOT_REPORTED, type Finding, type Report } from "./report";

const CAYMAN_DIMENSIONS = {
  identity: { score: 30, weight: "20%", tier: "LOW" },
  screening: { score: 100, weight: "30%", tier: "CRITICAL" },
  corporate_ubo: { score: 40, weight: "15%", tier: "MEDIUM" },
  regulatory: { score: 100, weight: "25%", tier: "CRITICAL" },
  transaction: { score: 90, weight: "10%", tier: "CRITICAL" },
};

function finding(overrides: Partial<Finding>): Finding {
  return {
    id: "finding-1",
    category: "screening",
    kind: "sanctions_match",
    scope: "sanctions",
    value: true,
    summary: "A finding",
    evidence_refs: ["evidence-1"],
    source: "demo_profile",
    source_at: null,
    observed_at: "2026-11-18T21:35:47Z",
    uncertainty: "observed",
    review_status: "pending",
    policy_version: "argus-risk-v1",
    ...overrides,
  };
}

describe("scoreWorking", () => {
  it("works out each dimension's points and the total as the report does", () => {
    const { rows, total } = scoreWorking(CAYMAN_DIMENSIONS);
    expect(rows.map((row) => row.key)).toEqual([
      "identity",
      "screening",
      "corporate_ubo",
      "regulatory",
      "transaction",
    ]);
    expect(rows.map((row) => row.weight)).toEqual([0.2, 0.3, 0.15, 0.25, 0.1]);
    expect(rows.map((row) => row.points)).toEqual([6, 30, 6, 25, 9]);
    expect(total).toBe(76);
  });

  it("keeps one decimal place", () => {
    const { total } = scoreWorking({
      ...CAYMAN_DIMENSIONS,
      identity: { score: 31, weight: "20%" },
    });
    expect(total).toBe(76.2);
  });

  it("gives no total when a dimension has no weight", () => {
    const { rows, total } = scoreWorking({ ...CAYMAN_DIMENSIONS, regulatory: { score: 100 } });
    expect(rows[3].points).toBeUndefined();
    expect(total).toBeUndefined();
  });

  it("still lists the five dimensions for a report without scores", () => {
    const { rows, total } = scoreWorking(undefined);
    expect(rows).toHaveLength(5);
    expect(rows.every((row) => row.points === undefined)).toBe(true);
    expect(total).toBeUndefined();
  });
});

describe("groupFindings", () => {
  it("files each finding under its dimension, potential before unknown before observed", () => {
    const observed = finding({ id: "a", uncertainty: "observed", kind: "pep_match", scope: "pep" });
    const potential = finding({ id: "b", uncertainty: "potential" });
    const unknown = finding({ id: "c", uncertainty: "unknown", kind: "adverse_media_match" });
    const corporate = finding({ id: "d", category: "corporate", kind: "corporate_flag" });
    const { byDimension } = groupFindings([observed, potential, unknown, corporate]);
    expect(byDimension.screening.map((f) => f.id)).toEqual(["b", "c", "a"]);
    expect(byDimension.corporate_ubo.map((f) => f.id)).toEqual(["d"]);
    expect(byDimension.regulatory).toEqual([]);
  });

  it("folds completed checks into one list and keeps a check that did not run", () => {
    const checks = ["sanctions", "pep", "adverse_media"].map((scope) =>
      finding({ id: scope, kind: "assessment", scope, value: "completed", summary: "" }),
    );
    const missed = finding({
      id: "missed",
      category: "transaction",
      kind: "assessment",
      scope: "transaction",
      value: "not_assessed",
      uncertainty: "unknown",
      summary: "⚠️ Transaction assessment did not run",
    });
    const { byDimension, checksCompleted } = groupFindings([...checks, missed]);
    expect(checksCompleted.screening).toEqual(["sanctions", "pep", "adverse_media"]);
    expect(byDimension.screening).toEqual([]);
    expect(byDimension.transaction.map((f) => f.id)).toEqual(["missed"]);
  });

  it("gives empty lists for a report without findings", () => {
    const { byDimension, checksCompleted } = groupFindings(undefined);
    expect(Object.values(byDimension).every((list) => list.length === 0)).toBe(true);
    expect(Object.values(checksCompleted).every((list) => list.length === 0)).toBe(true);
  });
});

describe("finding wording", () => {
  it("says each uncertainty in words", () => {
    expect(uncertaintyLabel("observed")).toBe("Observed");
    expect(uncertaintyLabel("potential")).toBe("Potential: a person must confirm");
    expect(uncertaintyLabel("unknown")).toBe("Unknown: not assessed");
  });

  it("drops the warning sign that starts some summaries", () => {
    expect(findingTitle(finding({ summary: "⚠️ Potential sanctions match" }))).toBe(
      "Potential sanctions match",
    );
    expect(findingTitle(finding({ summary: "PEP identified" }))).toBe("PEP identified");
  });

  it("names each check", () => {
    expect(["identity", "sanctions", "pep", "adverse_media", "other"].map(checkLabel)).toEqual([
      "Identity",
      "Sanctions",
      "PEP",
      "Adverse media",
      "other",
    ]);
  });
});

describe("formatTime", () => {
  it("writes a time for people, in the zone given", () => {
    expect(formatTime("2026-11-18T21:35:50.953960+00:00", "en-GB", "UTC")).toBe(
      "18 Nov 2026, 21:35",
    );
  });

  it("says when there is no usable time", () => {
    expect(formatTime(undefined)).toBe(NOT_REPORTED);
    expect(formatTime(null)).toBe(NOT_REPORTED);
    expect(formatTime("nonsense")).toBe(NOT_REPORTED);
  });
});

describe("actionsBesidesObligations", () => {
  it("leaves out actions already listed as obligations", () => {
    expect(actionsBesidesObligations(["a", "b", "c"], ["b"])).toEqual(["a", "c"]);
    expect(actionsBesidesObligations(undefined, ["b"])).toEqual([]);
    expect(actionsBesidesObligations(["a"], undefined)).toEqual(["a"]);
  });
});

describe("isSanctionsHold", () => {
  it("is true only when the sanctions match sets the tier", () => {
    expect(isSanctionsHold({ risk_summary: { tier_basis: "sanctions_match" } })).toBe(true);
    expect(isSanctionsHold({ risk_summary: { tier_basis: "score" } })).toBe(false);
    expect(isSanctionsHold({})).toBe(false);
  });
});

describe("investigationSummary", () => {
  it("counts the agents, the time and the recorded profiles", () => {
    const trace = {
      agents_invoked: ["identity", "screening", "corporate", "transaction", "compliance"],
      agent_sources: {
        identity: "demo_profile",
        screening: "demo_profile",
        corporate: "demo_profile",
        transaction: "demo_profile",
        compliance: "computed",
      },
    };
    expect(investigationSummary(trace, 4.4)).toBe(
      "5 agents finished in 4.4 s; 4 from recorded demo profiles",
    );
  });

  it("leaves out what was not reported", () => {
    expect(investigationSummary({ agents_invoked: ["identity"], agent_sources: {} })).toBe(
      "1 agent finished",
    );
  });
});

describe("sanctionsListing", () => {
  const report: Report = {
    findings: [finding({ evidence_refs: ["evidence-s"] })],
    evidence: {
      "evidence-s": {
        id: "evidence-s",
        source: "demo_profile",
        reference: {
          knowledge_base: "sanctions",
          document: "synthetic_sanctions_watchlist.json",
          snippet_id: "demo-high-001",
          program: "Narcotics Trafficking",
          is_active: true,
        },
        data: { type: "sanctions", match: "Strong sanctions-adjacent match", confidence: 0.93 },
        source_at: null,
      },
    },
  };

  it("reads the listing behind the sanctions finding", () => {
    expect(sanctionsListing(report)).toEqual({
      programme: "Narcotics Trafficking",
      entryId: "demo-high-001",
      active: true,
      match: "Strong sanctions-adjacent match",
      sourceScore: 0.93,
      document: "synthetic_sanctions_watchlist.json",
    });
  });

  it("is undefined without a sanctions finding", () => {
    expect(sanctionsListing({ findings: [finding({ kind: "pep_match" })] })).toBeUndefined();
    expect(sanctionsListing({})).toBeUndefined();
  });
});
