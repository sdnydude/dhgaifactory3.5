"use client";

import { useState } from "react";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";
import { useAgentsStore } from "@/stores/agents-store";
import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

const PIPELINE_ORDER = [
  "research",
  "clinical_practice",
  "gap_analysis",
  "learning_objectives",
  "needs_assessment",
  "curriculum_design",
  "research_protocol",
  "marketing_plan",
  "grant_writer",
  "prose_quality_1",
  "prose_quality_2",
  "compliance_review",
];

const AGENT_LABELS: Record<string, string> = {
  research: "Research",
  clinical_practice: "Clinical Practice",
  gap_analysis: "Gap Analysis",
  learning_objectives: "Learning Objectives",
  needs_assessment: "Needs Assessment",
  curriculum_design: "Curriculum Design",
  research_protocol: "Research Protocol",
  marketing_plan: "Marketing Plan",
  grant_writer: "Grant Writer",
  prose_quality_1: "Prose QA 1",
  prose_quality_2: "Prose QA 2",
  compliance_review: "Compliance",
};

const STATUS_COLORS: Record<string, string> = {
  complete: "bg-green-500",
  running: "bg-orange-500 animate-pulse",
  failed: "bg-red-500",
  pending: "bg-gray-300 dark:bg-gray-600",
};

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${s % 60}s`;
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

interface TimelineTabProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

export function TimelineTab({ agent, state }: TimelineTabProps) {
  const [renderTime] = useState(() => Date.now());
  const tokenUsage = useAgentsStore((s) => s.tokenUsage);
  const streamEvents = useAgentsStore((s) => s.streamEvents);

  if (!state) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No timeline data available
      </div>
    );
  }

  const timingData = state.timingData;
  const hasTimingData = Object.keys(timingData).length > 0;

  if (!hasTimingData && streamEvents.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Timeline unavailable &mdash; view in LangSmith
      </div>
    );
  }

  // Calculate timeline bounds
  let minTime = Infinity;
  let maxTime = 0;

  const agentBars: Array<{
    name: string;
    label: string;
    startMs: number;
    endMs: number;
    status: string;
  }> = [];

  for (const agentKey of PIPELINE_ORDER) {
    const timing = timingData[agentKey];
    if (!timing?.startedAt) continue;

    const startMs = new Date(timing.startedAt).getTime();
    const endMs = timing.completedAt
      ? new Date(timing.completedAt).getTime()
      : renderTime;

    minTime = Math.min(minTime, startMs);
    maxTime = Math.max(maxTime, endMs);

    const isComplete = state.completedOutputs.some((k) =>
      k.toLowerCase().includes(agentKey.replace(/_/g, "")),
    );
    const isCurrent = state.currentStep === agentKey;
    const hasFailed = state.errors.some(
      (e) => String(e.agent) === agentKey,
    );

    agentBars.push({
      name: agentKey,
      label: AGENT_LABELS[agentKey] ?? agentKey,
      startMs,
      endMs,
      status: hasFailed
        ? "failed"
        : isComplete
          ? "complete"
          : isCurrent
            ? "running"
            : "pending",
    });
  }

  const totalDuration = maxTime - minTime || 1;

  const pipelineDuration = formatMs(totalDuration);
  const totalTokens = tokenUsage.inputTokens + tokenUsage.outputTokens;
  const totalCost =
    totalTokens > 0
      ? `$${((tokenUsage.inputTokens * 3 + tokenUsage.outputTokens * 15) / 1_000_000).toFixed(4)}`
      : "\u2014";

  return (
    <TooltipProvider>
      <div className="space-y-1">
        {agentBars.map((bar) => {
          const leftPercent = ((bar.startMs - minTime) / totalDuration) * 100;
          const widthPercent = Math.max(
            ((bar.endMs - bar.startMs) / totalDuration) * 100,
            2,
          );
          const duration = formatMs(bar.endMs - bar.startMs);

          return (
            <div
              key={bar.name}
              className="grid grid-cols-[140px_1fr] gap-3 items-center"
            >
              <span className="text-[11px] text-right truncate text-muted-foreground">
                {bar.label}
              </span>
              <div className="relative h-6 bg-muted/30 rounded">
                <Tooltip>
                  <TooltipTrigger>
                    <div
                      className={`absolute top-0.5 bottom-0.5 rounded ${STATUS_COLORS[bar.status] ?? STATUS_COLORS.pending}`}
                      style={{
                        left: `${leftPercent}%`,
                        width: `${widthPercent}%`,
                        minWidth: "8px",
                      }}
                    >
                      {widthPercent > 15 && (
                        <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-[9px] text-white/80 font-mono">
                          {duration}
                        </span>
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs">
                      {bar.label}: {duration}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          );
        })}

        {/* Summary row */}
        <div className="grid grid-cols-[140px_1fr] gap-3 items-center pt-2 mt-2 border-t border-border">
          <span className="text-[11px] text-right font-medium">Total</span>
          <div className="flex gap-4 text-[11px] text-muted-foreground">
            <span>{pipelineDuration}</span>
            <span>{formatTokens(totalTokens)} tokens</span>
            <span>{totalCost}</span>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
