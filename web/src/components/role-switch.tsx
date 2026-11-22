"use client";

import { useId } from "react";

import { useRole } from "@/components/use-review";
import type { Role } from "@/lib/review-store";

/** The demo review's role, chosen in the header; one browser plays both. */
export function RoleSwitch() {
  const id = useId();
  const [role, setRole] = useRole();
  return (
    <div className="flex items-center gap-2 text-sm">
      <label htmlFor={id} className="text-muted-foreground">
        Role
      </label>
      <select
        id={id}
        value={role}
        onChange={(event) => setRole(event.target.value as Role)}
        className="h-8 rounded-lg border border-input bg-card px-2 font-medium outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <option value="analyst">Analyst</option>
        <option value="approver">Approver</option>
      </select>
    </div>
  );
}
