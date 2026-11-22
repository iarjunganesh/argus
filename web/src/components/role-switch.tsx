"use client";

import { useRole } from "@/components/use-review";
import type { Role } from "@/lib/review-store";

/** The demo review's role, chosen in the header; one browser plays both. */
export function RoleSwitch() {
  const [role, setRole] = useRole();
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">Role</span>
      <select
        value={role}
        onChange={(event) => setRole(event.target.value as Role)}
        className="h-8 rounded-lg border border-input bg-card px-2 font-medium outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <option value="analyst">Analyst</option>
        <option value="approver">Approver</option>
      </select>
    </label>
  );
}
