import { cn } from "cn";
import { CircleCheck, CircleDashed, CircleX, LoaderCircle } from "lucide-react";

import {
  durationSeconds,
  type AgentPhase,
  type AgentProgress,
  type Progress,
} from "@/lib/progress";
import { AGENTS, sourceLabel } from "@/lib/report";

const PHASES: Record<AgentPhase, { label: string; icon: typeof CircleCheck }> = {
  waiting: { label: "Waiting", icon: CircleDashed },
  running: { label: "Running", icon: LoaderCircle },
  done: { label: "Done", icon: CircleCheck },
  failed: { label: "Unavailable", icon: CircleX },
};

function AgentNode({
  name,
  does,
  progress,
  joined,
}: {
  name: string;
  does: string;
  progress: AgentProgress;
  joined?: boolean;
}) {
  const phase = PHASES[progress.phase];
  const Icon = phase.icon;
  const seconds = durationSeconds(progress.startedAt, progress.finishedAt);
  return (
    <div
      data-phase={progress.phase}
      className={cn(
        "relative h-full rounded-lg border bg-card px-4 py-3",
        progress.phase === "running" && "border-primary ring-2 ring-primary/30",
        progress.phase === "failed" && "border-destructive",
        // The line from each parallel agent to the bus that joins them.
        joined &&
          "md:after:absolute md:after:top-1/2 md:after:left-full md:after:w-5 md:after:border-t",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold">{name} agent</h3>
        <span className="flex items-center gap-1.5 text-sm">
          <Icon
            aria-hidden
            className={cn(
              "size-4",
              progress.phase === "running" && "animate-spin text-primary",
              progress.phase === "done" && "text-primary",
              progress.phase === "failed" && "text-destructive",
            )}
          />
          <span>
            {phase.label}
            {seconds !== undefined && (
              <span className="text-muted-foreground tabular-nums">
                {seconds < 0.1 ? " in under 0.1 s" : ` in ${seconds} s`}
              </span>
            )}
          </span>
        </span>
      </div>
      <p className="text-sm text-muted-foreground">{does}</p>
      {progress.source !== undefined && (
        <p className="mt-1 text-sm">
          <span className="text-muted-foreground">Result: </span>
          {sourceLabel(progress.source)}
          {progress.fallbacks.length > 0 && ` (${progress.fallbacks.join(", ")})`}
        </p>
      )}
    </div>
  );
}

/**
 * The workflow as it runs: four agents in parallel, joined into the compliance agent, which
 * scores the case. The layout draws the same fan-out and fan-in as the orchestrator.
 */
export function InvestigationFlow({ progress }: { progress: Progress }) {
  const parallel = AGENTS.filter((agent) => agent.id !== "compliance");
  const compliance = AGENTS.find((agent) => agent.id === "compliance")!;
  return (
    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_2.5rem_minmax(0,1fr)] md:gap-0">
      <div>
        <p className="mb-2 text-sm text-muted-foreground">In parallel</p>
        <ol className="grid auto-rows-fr gap-3">
          {parallel.map((agent) => (
            <li key={agent.id}>
              <AgentNode name={agent.name} does={agent.does} progress={progress[agent.id]} joined />
            </li>
          ))}
        </ol>
      </div>
      <div aria-hidden className="relative mt-7 hidden md:block">
        {/* The bus runs from the first agent's centre to the last one's (rows are 0.75rem apart). */}
        <span className="absolute top-[calc((100%-2.25rem)/8)] bottom-[calc((100%-2.25rem)/8)] left-5 border-l" />
        <span className="absolute top-1/2 right-0 left-5 border-t" />
      </div>
      <div className="flex flex-col">
        <p className="mb-2 text-sm text-muted-foreground">Then</p>
        <div className="flex flex-1 items-center">
          <div className="w-full">
            <AgentNode
              name={compliance.name}
              does={compliance.does}
              progress={progress.compliance}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
