"use client";

import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

interface OutputsTabProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

export function OutputsTab({ agent, state }: OutputsTabProps) {
  return (
    <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
      Outputs tab — {agent.graphId}
    </div>
  );
}
