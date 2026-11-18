import { describe, expect, it } from "vitest";

import {
  DAY_MS,
  demoCaseIndex,
  forgetReport,
  loadQueue,
  queueRows,
  rawQueue,
  recordRun,
  type QueueEntry,
} from "./queue";

function memoryStorage(): Storage {
  const items = new Map<string, string>();
  return {
    get length() {
      return items.size;
    },
    clear: () => items.clear(),
    getItem: (key) => items.get(key) ?? null,
    key: (index) => [...items.keys()][index] ?? null,
    removeItem: (key) => void items.delete(key),
    setItem: (key, value) => void items.set(key, String(value)),
  };
}

function blockedStorage(): Storage {
  const fail = () => {
    throw new Error("blocked");
  };
  return {
    length: 0,
    clear: fail,
    getItem: fail,
    key: fail,
    removeItem: fail,
    setItem: fail,
  };
}

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
