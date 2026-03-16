"use client";

import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

interface DetailTabProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

export function DetailTab({ agent, state }: DetailTabProps) {
  return (
    <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
      Detail tab — {agent.graphId}
    </div>
  );
}
