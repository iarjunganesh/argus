import { cn } from "cn";

import { tierTone } from "@/lib/report";

const TONES = {
  low: "bg-risk-low",
  medium: "bg-risk-medium",
  high: "bg-risk-high",
  critical: "bg-risk-critical",
  unknown: "bg-risk-unknown",
} as const;

/** The tier as white text on its audited colour. The word carries the meaning, not the colour. */
export function TierBadge({ tier, className }: { tier?: string; className?: string }) {
  return (
    <span
      data-tone={tierTone(tier)}
      className={cn(
        "inline-block rounded-md px-2 py-0.5 text-sm font-semibold text-risk-foreground",
        TONES[tierTone(tier)],
        className,
      )}
    >
      {tier || "UNKNOWN"}
    </span>
  );
}
