"use client";

import { PIPELINE_STEPS } from "@/types/cme";
import { PipelineStep, type StepStatus } from "./pipeline-step";
import type { ExecutionStatus } from "@/types/cme";

interface PipelineNavProps {
  pipelineStatus: ExecutionStatus | null;
  selectedStep: string | null;
  onSelectStep: (stepId: string) => void;
}

function getStepStatus(stepId: string, status: ExecutionStatus | null): StepStatus {
  if (!status) return "pending";
  if (status.agents_completed.some((a) => a === stepId || stepId.startsWith(a))) return "completed";
  if (status.current_agent === stepId) return "active";
  if (status.errors.some((e) => (e as Record<string, string>).agent === stepId)) return "error";
  return "pending";
}

export function PipelineNav({ pipelineStatus, selectedStep, onSelectStep }: PipelineNavProps) {
  return (
    <div className="w-[220px] shrink-0 border-r border-border p-3 space-y-0.5 overflow-auto">
      <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide px-3 mb-2">
        Pipeline
      </h3>
      {PIPELINE_STEPS.map((step) => (
        <PipelineStep
          key={step.id}
          label={step.label}
          status={getStepStatus(step.id, pipelineStatus)}
          selected={selectedStep === step.id}
          onClick={() => onSelectStep(step.id)}
        />
      ))}
    </div>
  );
}
