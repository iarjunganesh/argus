// The six demo scenarios from the README. Their parallel-agent results come from recorded demo
// profiles in the API (src/argus/utils/demo_profiles.py); the compliance step runs live.

import type { AssessmentRequest } from "./api";

export interface DemoCase extends AssessmentRequest {
  origin: "Synthetic" | "Public record";
}

export const DEMO_CASES: DemoCase[] = [
  {
    entity_name: "Synthetic Holdings B.V.",
    entity_type: "corporate",
    jurisdiction: "NL",
    origin: "Synthetic",
  },
  {
    entity_name: "Jane Synthetic",
    entity_type: "individual",
    jurisdiction: "DE",
    origin: "Synthetic",
  },
  {
    entity_name: "Cayman Synth Capital",
    entity_type: "corporate",
    jurisdiction: "KY",
    origin: "Synthetic",
  },
  {
    entity_name: "Wirecard AG",
    entity_type: "corporate",
    jurisdiction: "DE",
    origin: "Public record",
  },
  {
    entity_name: "Danske Bank A/S",
    entity_type: "corporate",
    jurisdiction: "DK",
    origin: "Public record",
  },
  {
    entity_name: "Westpac Banking Corporation",
    entity_type: "corporate",
    jurisdiction: "AU",
    origin: "Public record",
  },
];

/**
 * Set at build time. A public site, like its API (`ARGUS_DEMO_ONLY`), runs only the synthetic
 * cases, so no visitor's input names a real person.
 */
export const DEMO_ONLY = process.env.NEXT_PUBLIC_ARGUS_DEMO_ONLY === "true";

/** The demo cases the site offers: only the synthetic ones when it is demo-only. */
export function offeredDemoCases(demoOnly: boolean = DEMO_ONLY): DemoCase[] {
  return demoOnly ? DEMO_CASES.filter((demo) => demo.origin === "Synthetic") : DEMO_CASES;
}

/** How long the API keeps a report (REPORT_RETENTION_SECONDS in the API). */
export const RETENTION_NOTICE = "Reports are deleted 24 hours after their last update.";
