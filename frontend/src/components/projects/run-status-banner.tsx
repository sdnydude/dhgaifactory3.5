"use client";

import { AlertTriangle, Ban, RotateCcw } from "lucide-react";
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

  // Only show for terminal failure states. Complete runs get their own
  // success affordance elsewhere; processing runs don't need a banner.
  const terminalBad =
    project.status === CMEProjectStatus.FAILED ||
    project.status === CMEProjectStatus.CANCELLED;
  if (!terminalBad) return null;

  const run = latestRun(runsByProject[project.id]);
  const isCancelled = project.status === CMEProjectStatus.CANCELLED;
  const Icon = isCancelled ? Ban : AlertTriangle;

  async function handleRerun() {
    setRerunning(true);
    await rerunPipeline(project.id);
    setRerunning(false);
  }

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
