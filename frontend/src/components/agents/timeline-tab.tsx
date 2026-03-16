"use client";

import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

interface TimelineTabProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

export function TimelineTab({ agent, state }: TimelineTabProps) {
  return (
    <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
      Timeline tab — {agent.graphId}
    </div>
  );
}
