"use client";

import type { RunningAgent } from "@/lib/agentsApi";

interface StreamTabProps {
  agent: RunningAgent;
}

export function StreamTab({ agent }: StreamTabProps) {
  return (
    <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
      Stream tab — {agent.graphId}
    </div>
  );
}
