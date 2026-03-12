"use client";

import { cn } from "@/lib/utils";
import { CheckCircle2, Circle, Loader2, AlertCircle } from "lucide-react";
import type { ThreadState } from "@/lib/agentsApi";

interface Step {
  key: string;
  label: string;
}

const RECIPE_STEPS: Record<string, Step[]> = {
  needs_package: [
    { key: "initialize", label: "Initialize" },
    { key: "early_research", label: "Research + Clinical" },
    { key: "gap_analysis", label: "Gap Analysis" },
    { key: "learning_objectives", label: "Learning Objectives" },
    { key: "needs_assessment", label: "Needs Assessment" },
    { key: "prose_quality", label: "Prose QA" },
    { key: "human_review", label: "Human Review" },
  ],
  curriculum_package: [
    { key: "initialize", label: "Initialize" },
    { key: "early_research", label: "Research + Clinical" },
    { key: "gap_analysis", label: "Gap Analysis" },
    { key: "learning_objectives", label: "Learning Objectives" },
    { key: "needs_assessment", label: "Needs Assessment" },
    { key: "prose_quality", label: "Prose QA (1)" },
    { key: "design_phase", label: "Curriculum + Protocol + Marketing" },
    { key: "human_review", label: "Human Review" },
  ],
  grant_package: [
    { key: "initialize", label: "Initialize" },
    { key: "early_research", label: "Research + Clinical" },
    { key: "gap_analysis", label: "Gap Analysis" },
    { key: "learning_objectives", label: "Learning Objectives" },
    { key: "needs_assessment", label: "Needs Assessment" },
    { key: "prose_quality", label: "Prose QA (1)" },
    { key: "design_phase", label: "Curriculum + Protocol + Marketing" },
    { key: "grant_writer", label: "Grant Writer" },
    { key: "prose_quality_2", label: "Prose QA (2)" },
    { key: "compliance", label: "Compliance" },
    { key: "human_review", label: "Human Review" },
  ],
  full_pipeline: [
    { key: "initialize", label: "Initialize" },
    { key: "early_research", label: "Research + Clinical" },
    { key: "gap_analysis", label: "Gap Analysis" },
    { key: "learning_objectives", label: "Learning Objectives" },
    { key: "needs_assessment", label: "Needs Assessment" },
    { key: "prose_quality", label: "Prose QA (1)" },
    { key: "design_phase", label: "Curriculum + Protocol + Marketing" },
    { key: "grant_writer", label: "Grant Writer" },
    { key: "prose_quality_2", label: "Prose QA (2)" },
    { key: "compliance", label: "Compliance" },
    { key: "human_review", label: "Human Review" },
  ],
};

const OUTPUT_MAP: Record<string, string> = {
  early_research: "research_output",
  gap_analysis: "gap_analysis_output",
  learning_objectives: "learning_objectives_output",
  needs_assessment: "needs_assessment_output",
  prose_quality: "prose_quality_pass_1",
  design_phase: "curriculum_output",
  grant_writer: "grant_package_output",
  prose_quality_2: "prose_quality_pass_2",
  compliance: "compliance_result",
};

function stepStatus(
  step: string,
  currentStep: string,
  completedOutputs: string[],
  steps: Step[],
): "done" | "active" | "pending" {
  if (step === "initialize" && currentStep !== "") return "done";
  if (OUTPUT_MAP[step] && completedOutputs.includes(OUTPUT_MAP[step])) return "done";
  if (currentStep.startsWith(step) || currentStep.includes(step)) return "active";
  if (step === "human_review" && currentStep.includes("human_review")) return "active";

  const stepIdx = steps.findIndex((s) => s.key === step);
  const currentIdx = steps.findIndex(
    (s) => currentStep.startsWith(s.key) || currentStep.includes(s.key),
  );
  if (currentIdx > stepIdx) return "done";

  return "pending";
}

interface PipelineProgressProps {
  state: ThreadState;
  graphId?: string;
}

export function PipelineProgress({ state, graphId }: PipelineProgressProps) {
  const steps = RECIPE_STEPS[graphId ?? ""] ?? RECIPE_STEPS.needs_package;

  return (
    <div className="space-y-1">
      <h4 className="text-xs font-semibold text-muted-foreground mb-2">Pipeline Progress</h4>
      <div className="flex items-center gap-1">
        {steps.map((step, i) => {
          const s = stepStatus(step.key, state.currentStep, state.completedOutputs, steps);
          return (
            <div key={step.key} className="flex items-center gap-1">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex items-center justify-center h-6 w-6 rounded-full text-[9px] font-medium",
                    s === "done" && "bg-green-500/15 text-green-600 dark:text-green-400",
                    s === "active" && "bg-dhg-orange/15 text-dhg-orange ring-2 ring-dhg-orange/30",
                    s === "pending" && "bg-muted text-muted-foreground",
                  )}
                >
                  {s === "done" && <CheckCircle2 className="h-3.5 w-3.5" />}
                  {s === "active" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  {s === "pending" && <Circle className="h-3 w-3" />}
                </div>
                <span className={cn(
                  "text-[9px] mt-1 text-center leading-tight max-w-[72px]",
                  s === "active" ? "text-foreground font-medium" : "text-muted-foreground",
                )}>
                  {step.label}
                </span>
              </div>
              {i < steps.length - 1 && (
                <div className={cn(
                  "h-px w-4 mb-4",
                  s === "done" ? "bg-green-500/40" : "bg-border",
                )} />
              )}
            </div>
          );
        })}
      </div>
      {state.errors.length > 0 && (
        <div className="flex items-start gap-1.5 mt-2 text-[10px] text-destructive">
          <AlertCircle className="h-3 w-3 mt-0.5 shrink-0" />
          <span>{state.errors.length} error{state.errors.length !== 1 ? "s" : ""} — latest: {String((state.errors.at(-1) as Record<string, unknown>)?.message ?? "unknown").slice(0, 80)}</span>
        </div>
      )}
    </div>
  );
}
