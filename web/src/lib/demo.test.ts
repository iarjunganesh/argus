import { describe, expect, it } from "vitest";

import { DEMO_CASES } from "./demo";

describe("the demo cases", () => {
  it("are six invented entities, each listed once", () => {
    const names = DEMO_CASES.map((demo) => demo.entity_name);
    expect(names).toHaveLength(6);
    expect(new Set(names).size).toBe(6);
    expect(names.every((name) => /synth/i.test(name))).toBe(true);
  });
});
