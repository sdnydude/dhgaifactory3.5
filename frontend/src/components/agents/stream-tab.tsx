"use client";

import { LogStream } from "./log-stream";
import { useAgentsStore } from "@/stores/agents-store";
import type { RunningAgent } from "@/lib/agentsApi";

interface StreamTabProps {
  agent: RunningAgent;
}

export function StreamTab({ agent }: StreamTabProps) {
  const streamEvents = useAgentsStore((s) => s.streamEvents);
  const streamStatus = useAgentsStore((s) => s.streamStatus);

  const logs = streamEvents.map((evt) => ({
    id: evt.id,
    timestamp: evt.timestamp,
    source: evt.agentName,
    message: evt.message,
    level: evt.level,
  }));

  const isIdle = agent.status !== "busy" && streamStatus === "idle";

  if (isIdle) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No active stream &mdash; this thread is not running.
      </div>
    );
  }

  const footer =
    streamStatus === "ended"
      ? `Stream ended at ${new Date().toLocaleTimeString()}`
      : undefined;

  return (
    <div className="h-full">
      <LogStream logs={logs} footer={footer} />
    </div>
  );
}
