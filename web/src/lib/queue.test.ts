import { describe, expect, it } from "vitest";

import {
  DAY_MS,
  demoCaseIndex,
  forgetReport,
  loadQueue,
  queueRows,
  rawQueue,
  recordRun,
  runEntry,
  type QueueEntry,
} from "./queue";
import { blockedStorage, memoryStorage } from "./test-storage";

const NOW = 1_800_000_000_000;
const entry = (reportId: string, tier?: string, at = NOW): QueueEntry => ({
  reportId,
  tier,
  score: tier ? 50 : undefined,
  at,
});

describe("the cases queue store", () => {
  it("keeps each demo case's last run", () => {
    const storage = memoryStorage();
    expect(recordRun(2, entry("argus-rpt-a", "CRITICAL"), storage)).toBe(true);
    expect(loadQueue(storage, NOW)).toEqual({ 2: entry("argus-rpt-a", "CRITICAL") });
  });

  it("keeps the newer run when an older report is reopened", () => {
    const storage = memoryStorage();
    recordRun(2, entry("argus-rpt-new", "CRITICAL", NOW), storage);
    expect(recordRun(2, entry("argus-rpt-old", "LOW", NOW - 60_000), storage)).toBe(false);
    expect(loadQueue(storage, NOW)[2]?.reportId).toBe("argus-rpt-new");
  });

  it("drops a run older than a day, as the API drops its report", () => {
    const storage = memoryStorage();
    recordRun(1, entry("argus-rpt-old", "LOW", NOW - DAY_MS - 1), storage);
    recordRun(2, entry("argus-rpt-new", "CRITICAL", NOW - DAY_MS + 1), storage);
    expect(Object.keys(loadQueue(storage, NOW))).toEqual(["2"]);
  });

  it("forgets only the report the API no longer has", () => {
    const storage = memoryStorage();
    recordRun(1, entry("argus-rpt-a", "LOW"), storage);
    recordRun(2, entry("argus-rpt-b", "CRITICAL"), storage);
    forgetReport("argus-rpt-a", storage);
    expect(Object.keys(loadQueue(storage, NOW))).toEqual(["2"]);
  });

  it("works without storage and says nothing was kept", () => {
    expect(loadQueue(blockedStorage(), NOW)).toEqual({});
    expect(recordRun(2, entry("argus-rpt-a"), blockedStorage())).toBe(false);
    expect(() => forgetReport("argus-rpt-a", blockedStorage())).not.toThrow();
    expect(loadQueue(undefined, NOW)).toEqual({});
  });

  it("ignores what it cannot read", () => {
    const storage = memoryStorage();
    storage.setItem("argus:queue", "not json");
    expect(loadQueue(storage, NOW)).toEqual({});
  });

  it("never stores an entity's name", () => {
    const storage = memoryStorage();
    recordRun(2, entry("argus-rpt-a", "CRITICAL"), storage);
    expect(storage.getItem("argus:queue")).not.toMatch(/Cayman/);
  });
});

describe("demoCaseIndex", () => {
  it("finds a demo case by name and jurisdiction", () => {
    expect(demoCaseIndex({ name: "Cayman Synth Capital", jurisdiction: "KY" })).toBe(2);
    expect(demoCaseIndex({ name: "Cayman Synth Capital", jurisdiction: "DE" })).toBeUndefined();
    expect(demoCaseIndex({ name: "Someone Else", jurisdiction: "KY" })).toBeUndefined();
    expect(demoCaseIndex(undefined)).toBeUndefined();
  });
});

describe("queueRows", () => {
  it("puts the riskiest run cases first and cases not run last, each by name", () => {
    const rows = queueRows({
      0: entry("a", "MEDIUM"),
      2: entry("b", "CRITICAL"),
      5: entry("c", "LOW"),
    });
    expect(rows.map((row) => row.request.entity_name)).toEqual([
      "Cayman Synth Capital",
      "Synthetic Holdings B.V.",
      "Synthetic Pacific Banking Corporation",
      "Jane Synthetic",
      "Synthetic Nordic Bank A/S",
      "Synthetic Payments AG",
    ]);
    expect(rows[0].entry?.reportId).toBe("b");
    expect(rows[3].entry).toBeUndefined();
  });
});

describe("rawQueue", () => {
  it("returns what is stored, or an empty string when nothing can be read", () => {
    const storage = memoryStorage();
    expect(rawQueue(storage)).toBe("");
    recordRun(2, entry("argus-rpt-a", "CRITICAL"), storage);
    expect(rawQueue(storage)).toContain("argus-rpt-a");
    expect(rawQueue(blockedStorage())).toBe("");
  });
});

describe("runEntry", () => {
  it("dates a run by when its report was generated, not when it was opened", () => {
    const report = {
      generated_at: "2026-11-19T10:00:00Z",
      risk_summary: { overall_risk_tier: "LOW", overall_risk_score: 3 },
    };
    expect(runEntry("argus-rpt-a", report, NOW)).toEqual({
      reportId: "argus-rpt-a",
      tier: "LOW",
      score: 3,
      hold: false,
      edd: false,
      at: Date.parse("2026-11-19T10:00:00Z"),
    });
  });

  it("keeps what the demo review's rules need: the sanctions hold and enhanced due diligence", () => {
    const report = {
      generated_at: "2026-11-19T10:00:00Z",
      risk_summary: {
        overall_risk_tier: "CRITICAL",
        overall_risk_score: 76,
        tier_basis: "sanctions_match",
        edd_required: true,
      },
    };
    expect(runEntry("argus-rpt-a", report, NOW)).toMatchObject({ hold: true, edd: true });
  });

  it("falls back to now when the report has no usable time", () => {
    expect(runEntry("argus-rpt-a", {}, NOW).at).toBe(NOW);
    expect(runEntry("argus-rpt-a", { generated_at: "not a date" }, NOW).at).toBe(NOW);
  });
});
