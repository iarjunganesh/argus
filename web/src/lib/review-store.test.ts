import { describe, expect, it } from "vitest";

import { DAY_MS } from "./queue";
import { forgetSteps, loadRole, loadSteps, saveRole, saveSteps, type Step } from "./review-store";
import { blockedStorage, memoryStorage } from "./test-storage";

const NOW = Date.parse("2026-11-22T12:00:00Z");
const at = (ms: number) => new Date(ms).toISOString();

const CLEAR: Step = {
  reviewer: "analyst",
  action: "clear",
  rationale: "Different registration and jurisdiction.",
  decided_at: at(NOW - 120_000),
};
const APPROVE_EDD: Step = {
  reviewer: "analyst",
  action: "approve_edd",
  rationale: "Onboard with enhanced due diligence.",
  decided_at: at(NOW - 60_000),
};

describe("the demo review's steps", () => {
  it("keeps a report's steps in this browser", () => {
    const storage = memoryStorage();
    expect(saveSteps("argus-rpt-a", [CLEAR, APPROVE_EDD], storage)).toBe(true);
    expect(loadSteps("argus-rpt-a", storage, NOW)).toEqual({
      steps: [CLEAR, APPROVE_EDD],
      kept: true,
    });
    expect(loadSteps("argus-rpt-b", storage, NOW)).toEqual({ steps: [], kept: true });
  });

  it("stores them under the report ID, never the entity's name", () => {
    const storage = memoryStorage();
    saveSteps("argus-rpt-a", [CLEAR], storage);
    expect(storage.getItem("argus:review:argus-rpt-a")).toContain("clear");
    expect(storage.key(0)).toBe("argus:review:argus-rpt-a");
  });

  it("drops a review whose newest step is older than a day, as the API drops its report", () => {
    const storage = memoryStorage();
    const old = { ...CLEAR, decided_at: at(NOW - 2 * DAY_MS) };
    saveSteps(
      "argus-rpt-old",
      [old, { ...APPROVE_EDD, decided_at: at(NOW - DAY_MS - 1) }],
      storage,
    );
    saveSteps(
      "argus-rpt-new",
      [old, { ...APPROVE_EDD, decided_at: at(NOW - DAY_MS + 1) }],
      storage,
    );
    expect(loadSteps("argus-rpt-old", storage, NOW).steps).toEqual([]);
    expect(storage.getItem("argus:review:argus-rpt-old")).toBeNull();
    expect(loadSteps("argus-rpt-new", storage, NOW).steps).toHaveLength(2);
  });

  it("works without storage and says nothing is kept", () => {
    expect(loadSteps("argus-rpt-a", blockedStorage(), NOW)).toEqual({ steps: [], kept: false });
    expect(loadSteps("argus-rpt-a", undefined, NOW)).toEqual({ steps: [], kept: false });
    expect(saveSteps("argus-rpt-a", [CLEAR], blockedStorage())).toBe(false);
    expect(saveSteps("argus-rpt-a", [CLEAR], undefined)).toBe(false);
    expect(() => forgetSteps("argus-rpt-a", blockedStorage())).not.toThrow();
  });

  it("ignores what it cannot read", () => {
    const storage = memoryStorage();
    storage.setItem("argus:review:argus-rpt-a", "not json");
    storage.setItem("argus:review:argus-rpt-b", JSON.stringify({ reviewer: "analyst" }));
    storage.setItem("argus:review:argus-rpt-c", JSON.stringify([CLEAR, { action: "approve" }]));
    expect(loadSteps("argus-rpt-a", storage, NOW)).toEqual({ steps: [], kept: true });
    expect(loadSteps("argus-rpt-b", storage, NOW)).toEqual({ steps: [], kept: true });
    expect(loadSteps("argus-rpt-c", storage, NOW)).toEqual({ steps: [CLEAR], kept: true });
  });

  it("forgets the review of a report the API no longer has", () => {
    const storage = memoryStorage();
    saveSteps("argus-rpt-a", [CLEAR], storage);
    saveSteps("argus-rpt-b", [CLEAR], storage);
    forgetSteps("argus-rpt-a", storage);
    expect(loadSteps("argus-rpt-a", storage, NOW).steps).toEqual([]);
    expect(loadSteps("argus-rpt-b", storage, NOW).steps).toEqual([CLEAR]);
  });
});

describe("the demo role", () => {
  it("starts as the analyst", () => {
    expect(loadRole(memoryStorage())).toBe("analyst");
    expect(loadRole(blockedStorage())).toBe("analyst");
    expect(loadRole(undefined)).toBe("analyst");
  });

  it("keeps the chosen role", () => {
    const storage = memoryStorage();
    expect(saveRole("approver", storage)).toBe(true);
    expect(loadRole(storage)).toBe("approver");
    expect(saveRole("analyst", storage)).toBe(true);
    expect(loadRole(storage)).toBe("analyst");
  });

  it("ignores a stored value that is not a role, and says when it keeps nothing", () => {
    const storage = memoryStorage();
    storage.setItem("argus:role", "admin");
    expect(loadRole(storage)).toBe("analyst");
    expect(saveRole("approver", blockedStorage())).toBe(false);
  });
});
