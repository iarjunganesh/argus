import { describe, expect, it } from "vitest";

import { DEMO_CASES, offeredDemoCases } from "./demo";

describe("the demo cases offered", () => {
  it("are all six by default", () => {
    expect(offeredDemoCases(false)).toEqual(DEMO_CASES);
  });

  it("are only the synthetic ones on a demo-only site", () => {
    expect(offeredDemoCases(true).map((demo) => demo.entity_name)).toEqual([
      "Synthetic Holdings B.V.",
      "Jane Synthetic",
      "Cayman Synth Capital",
    ]);
  });
});
