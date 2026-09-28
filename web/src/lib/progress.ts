// The progress stream (GET /api/v1/kyc/stream/{id}) folded into one state per agent.

import { AGENTS, type AgentId } from "./report";

export type ProgressEvent =
  | { type: "agent_started"; agent: string; at: string }
  | {
      type: "agent_completed";
      agent: string;
      at: string;
      status?: string | null;
      source?: string | null;
      fallbacks?: string[];
    }
  | { type: "status"; report_id: string; status: string };

export type AgentPhase = "waiting" | "running" | "done" | "failed";

export interface AgentProgress {
  phase: AgentPhase;
  startedAt?: string;
  finishedAt?: string;
  source?: string | null;
  fallbacks: string[];
}

export type Progress = Record<AgentId, AgentProgress>;

export function initialProgress(): Progress {
  const waiting = (): AgentProgress => ({ phase: "waiting", fallbacks: [] });
  return {
    identity: waiting(),
    screening: waiting(),
    corporate: waiting(),
    transaction: waiting(),
    compliance: waiting(),
  };
}

function isAgent(agent: string): agent is AgentId {
  return AGENTS.some(({ id }) => id === agent);
}

/** The progress after one event. Events for agents the UI does not know are ignored. */
export function applyEvent(progress: Progress, event: ProgressEvent): Progress {
  if (event.type === "status" || !isAgent(event.agent)) return progress;
  const current = progress[event.agent];
  if (event.type === "agent_started") {
    return { ...progress, [event.agent]: { ...current, phase: "running", startedAt: event.at } };
  }
  return {
    ...progress,
    [event.agent]: {
      ...current,
      phase: event.status === "completed" ? "done" : "failed",
      finishedAt: event.at,
      source: event.source,
      fallbacks: event.fallbacks ?? [],
    },
  };
}

export function finishedCount(progress: Progress): number {
  return Object.values(progress).filter(
    (agent) => agent.phase === "done" || agent.phase === "failed",
  ).length;
}

/** Seconds between two ISO timestamps, to one decimal; undefined if either is missing. */
export function durationSeconds(start?: string, end?: string): number | undefined {
  if (!start || !end) return undefined;
  const ms = Date.parse(end) - Date.parse(start);
  return Number.isFinite(ms) ? Math.max(0, Math.round(ms / 100) / 10) : undefined;
}
