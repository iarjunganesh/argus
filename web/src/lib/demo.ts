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
