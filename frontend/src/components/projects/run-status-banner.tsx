"use client";

import { AlertTriangle, Ban, FileWarning, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useProjectsStore } from "@/stores/projects-store";
import type { CMEProjectDetail, PipelineRun } from "@/types/cme";
import { CMEProjectStatus } from "@/types/cme";
import { useState } from "react";

function latestRun(runs: PipelineRun[] | undefined): PipelineRun | null {
  if (!runs || runs.length === 0) return null;
  return runs[0]; // backend returns runs sorted by run_number DESC
}

export function RunStatusBanner({ project }: { project: CMEProjectDetail }) {
  const { runsByProject, rerunPipeline } = useProjectsStore();
  const [rerunning, setRerunning] = useState(false);

  const run = latestRun(runsByProject[project.id]);

  // Stale-intake variant: project intake has been edited since the latest run.
  // Suppress while a run is in flight (status would be processing) since the
  // running pipeline is locked to its snapshot anyway.
  const isProcessing = project.status === CMEProjectStatus.PROCESSING;
  const intakeIsStale =
    !isProcessing &&
    run !== null &&
    typeof run.intake_version_used === "number" &&
    project.intake_version > run.intake_version_used;

  const terminalBad =
    project.status === CMEProjectStatus.FAILED ||
    project.status === CMEProjectStatus.CANCELLED;

  async function handleRerun() {
    setRerunning(true);
    await rerunPipeline(project.id);
    setRerunning(false);
  }

  if (intakeIsStale) {
    return (
      <div className="border-b px-6 py-2.5 flex items-start gap-3 bg-amber-500/10 border-amber-500/30">
        <FileWarning className="h-4 w-4 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
        <div className="flex-1 min-w-0 space-y-0.5">
          <p className="text-xs font-medium">
            Intake updated since last run
          </p>
          <p className="text-xs text-muted-foreground">
            Run #{run!.run_number} used intake v{run!.intake_version_used}; current intake is v{project.intake_version}. Rerun to apply the changes.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRerun}
          disabled={rerunning}
          className="gap-1.5 shrink-0"
        >
          <RotateCcw className="h-3 w-3" />
          {rerunning ? "Starting..." : "Rerun"}
        </Button>
      </div>
    );
  }

  if (!terminalBad) return null;

  const isCancelled = project.status === CMEProjectStatus.CANCELLED;
  const Icon = isCancelled ? Ban : AlertTriangle;

  return (
    <div
      className={`border-b px-6 py-2.5 flex items-start gap-3 ${
        isCancelled
          ? "bg-muted/50 border-border"
          : "bg-destructive/10 border-destructive/30"
      }`}
    >
      <Icon
        className={`h-4 w-4 mt-0.5 shrink-0 ${
          isCancelled ? "text-muted-foreground" : "text-destructive"
        }`}
      />
      <div className="flex-1 min-w-0 space-y-0.5">
        <p className="text-xs font-medium">
          {isCancelled
            ? "This run was cancelled"
            : `Run ${run ? `#${run.run_number} ` : ""}failed`}
          {run?.final_agent && !isCancelled && (
            <span className="text-muted-foreground font-normal">
              {" "}at <span className="font-mono">{run.final_agent}</span>
            </span>
          )}
        </p>
        {run?.error_message && (
          <p className="text-xs text-destructive/90 font-mono truncate">
            {run.error_message}
          </p>
        )}
        {run?.reason && (
          <p className="text-xs text-muted-foreground italic truncate">
            &ldquo;{run.reason}&rdquo;
          </p>
        )}
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={handleRerun}
        disabled={rerunning}
        className="gap-1.5 shrink-0"
      >
        <RotateCcw className="h-3 w-3" />
        {rerunning ? "Starting..." : "Rerun"}
      </Button>
    </div>
  );
}
