// The six demo scenarios from the README, every one an invented entity. Their parallel-agent
// results come from recorded demo profiles in the API (src/argus/utils/demo_profiles.py); the
// compliance step runs live.

import type { AssessmentRequest } from "./api";

export const DEMO_CASES: AssessmentRequest[] = [
  {
    entity_name: "Synthetic Holdings B.V.",
    entity_type: "corporate",
    jurisdiction: "NL",
  },
  {
    entity_name: "Jane Synthetic",
    entity_type: "individual",
    jurisdiction: "DE",
  },
  {
    entity_name: "Cayman Synth Capital",
    entity_type: "corporate",
    jurisdiction: "KY",
  },
  {
    entity_name: "Synthetic Payments AG",
    entity_type: "corporate",
    jurisdiction: "DE",
  },
  {
    entity_name: "Synthetic Nordic Bank A/S",
    entity_type: "corporate",
    jurisdiction: "DK",
  },
  {
    entity_name: "Synthetic Pacific Banking Corporation",
    entity_type: "corporate",
    jurisdiction: "AU",
  },
];

/**
 * Set at build time. A public site, like its API (`ARGUS_DEMO_ONLY`), runs only the demo cases
 * and has no form, so no visitor's input names a real person.
 */
export const DEMO_ONLY = process.env.NEXT_PUBLIC_ARGUS_DEMO_ONLY === "true";

/** How long the API keeps a report (REPORT_RETENTION_SECONDS in the API). */
export const RETENTION_NOTICE = "Reports are deleted 24 hours after their last update.";
