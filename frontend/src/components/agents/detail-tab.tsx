"use client";

import { Clock, Hash, Shield, RotateCcw, Coins, Zap, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAgentsStore } from "@/stores/agents-store";
import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

interface DetailTabProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

function formatDuration(start: string, end: string): string {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

function formatTokens(n: number): string {
  if (n === 0) return "\u2014";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function estimateCost(input: number, output: number): string {
  if (input === 0 && output === 0) return "\u2014";
  const cost = (input * 3 + output * 15) / 1_000_000;
  return `$${cost.toFixed(4)}`;
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className="h-3 w-3 text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground">{label}</span>
      </div>
      <p className="text-xs font-medium truncate capitalize">{value}</p>
    </div>
  );
}

export function DetailTab({ agent, state }: DetailTabProps) {
  const tokenUsage = useAgentsStore((s) => s.tokenUsage);
  const retryRun = useAgentsStore((s) => s.retryRun);

  const duration =
    agent.updatedAt && agent.createdAt
      ? formatDuration(agent.createdAt, agent.updatedAt)
      : "\u2014";

  return (
    <div className="space-y-5">
      {/* Key Metrics */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        <MetricCard icon={Clock} label="Duration" value={duration} />
        <MetricCard
          icon={Hash}
          label="Step"
          value={state?.currentStep.replace(/_/g, " ") ?? "\u2014"}
        />
        <MetricCard icon={RotateCcw} label="Retries" value={String(state?.retryCount ?? 0)} />
        <MetricCard icon={Shield} label="Review Round" value={String(state?.reviewRound ?? 0)} />
        <MetricCard icon={Zap} label="Tokens" value={formatTokens(tokenUsage.inputTokens + tokenUsage.outputTokens)} />
        <MetricCard icon={Coins} label="Est. Cost" value={estimateCost(tokenUsage.inputTokens, tokenUsage.outputTokens)} />
      </div>

      {/* IDs */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-muted-foreground">Thread ID</span>
          <p className="font-mono truncate text-[10px]">{agent.threadId}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Run ID</span>
          <p className="font-mono truncate text-[10px]">{agent.runId}</p>
        </div>
        {state?.projectId && (
          <div>
            <span className="text-muted-foreground">Project ID</span>
            <p className="font-mono truncate text-[10px]">{state.projectId}</p>
          </div>
        )}
        {state?.lastCheckpoint && (
          <div>
            <span className="text-muted-foreground">Last Checkpoint</span>
            <p className="text-[10px]">
              {new Date(state.lastCheckpoint).toLocaleTimeString()} &mdash;{" "}
              {state.checkpointAgent.replace(/_/g, " ")}
            </p>
          </div>
        )}
      </div>

      {/* Errors */}
      {state && state.errors.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-destructive mb-2">
            Errors ({state.errors.length})
          </h4>
          <div className="space-y-1.5">
            {state.errors.map((err, i) => (
              <div
                key={i}
                className="flex items-start justify-between rounded-md bg-destructive/10 px-3 py-2"
              >
                <div className="text-[11px] text-destructive">
                  <span className="font-medium">
                    [{String(err.agent ?? "unknown")}]
                  </span>{" "}
                  {String(err.message ?? "Unknown error")}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-[10px] shrink-0 ml-2"
                  onClick={() => retryRun(agent.threadId)}
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Retry
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
