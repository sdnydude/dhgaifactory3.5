"use client";

import { Activity, Clock, Hash, GitBranch, FileText, Shield, RotateCcw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PipelineProgress } from "./pipeline-progress";
import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

interface AgentDetailProps {
  agent: RunningAgent | null;
  state: ThreadState | null;
}

const OUTPUT_LABELS: Record<string, string> = {
  research_output: "Research & Literature",
  clinical_output: "Clinical Practice",
  gap_analysis_output: "Gap Analysis",
  learning_objectives_output: "Learning Objectives",
  needs_assessment_output: "Needs Assessment",
  curriculum_output: "Curriculum Design",
  protocol_output: "Research Protocol",
  marketing_output: "Marketing Plan",
  grant_package_output: "Grant Package",
  prose_quality_pass_1: "Prose QA Pass 1",
  prose_quality_pass_2: "Prose QA Pass 2",
  compliance_result: "Compliance Review",
};

function StatusBadge({ status }: { status: string }) {
  const variant = status === "running" || status === "in_progress"
    ? "default"
    : status === "success" || status === "complete"
      ? "secondary"
      : status === "error" || status === "failed"
        ? "destructive"
        : "outline";
  return <Badge variant={variant}>{status}</Badge>;
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

export function AgentDetail({ agent, state }: AgentDetailProps) {
  if (!agent) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center">
        <Activity className="h-10 w-10 text-muted-foreground/50 mb-3" />
        <p className="text-sm text-muted-foreground">Select a thread to view details</p>
      </div>
    );
  }

  const duration = agent.updatedAt && agent.createdAt
    ? formatDuration(agent.createdAt, agent.updatedAt)
    : "—";

  return (
    <div className="p-4 space-y-5 overflow-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">{agent.graphId}</h3>
          {state?.projectName && (
            <p className="text-xs text-muted-foreground mt-0.5">{state.projectName}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={agent.status} />
          {state?.humanReviewStatus && (
            <Badge variant="outline" className="text-[9px]">Review: {state.humanReviewStatus}</Badge>
          )}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard icon={Clock} label="Duration" value={duration} />
        <MetricCard icon={Hash} label="Step" value={state?.currentStep.replace(/_/g, " ") ?? "—"} />
        <MetricCard icon={RotateCcw} label="Retries" value={String(state?.retryCount ?? 0)} />
        <MetricCard icon={Shield} label="Review Round" value={String(state?.reviewRound ?? 0)} />
      </div>

      {/* Pipeline Progress */}
      {state && <PipelineProgress state={state} graphId={agent.graphId} />}

      {/* Completed Outputs */}
      {state && state.completedOutputs.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground mb-2">Completed Agent Outputs</h4>
          <div className="grid grid-cols-2 gap-1.5">
            {state.completedOutputs.map((key) => (
              <div key={key} className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-green-500/10 text-[11px]">
                <FileText className="h-3 w-3 text-green-600 dark:text-green-400 shrink-0" />
                <span className="text-green-700 dark:text-green-300 truncate">
                  {OUTPUT_LABELS[key] ?? key.replace(/_/g, " ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

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
              {new Date(state.lastCheckpoint).toLocaleTimeString()} — {state.checkpointAgent.replace(/_/g, " ")}
            </p>
          </div>
        )}
      </div>

      {/* Errors */}
      {state && state.errors.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-destructive mb-2">Errors ({state.errors.length})</h4>
          <div className="space-y-1.5">
            {state.errors.map((err, i) => (
              <div key={i} className="rounded-md bg-destructive/10 px-3 py-2 text-[11px] text-destructive">
                <span className="font-medium">[{String(err.agent ?? "unknown")}]</span>{" "}
                {String(err.message ?? "Unknown error")}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string }) {
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
