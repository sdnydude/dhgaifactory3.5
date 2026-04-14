"use client";

import { useEffect, useState } from "react";
import { History, Clock, CheckCircle2, XCircle, Ban, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjectsStore } from "@/stores/projects-store";
import type { PipelineRun, PipelineRunStatus } from "@/types/cme";

const STATUS_META: Record<
  PipelineRunStatus,
  {
    label: string;
    icon: typeof CheckCircle2;
    variant: "default" | "secondary" | "destructive" | "outline";
    className: string;
  }
> = {
  processing: {
    label: "Running",
    icon: Loader2,
    variant: "default",
    className: "text-dhg-orange",
  },
  success: {
    label: "Success",
    icon: CheckCircle2,
    variant: "default",
    className: "text-green-600",
  },
  failed: {
    label: "Failed",
    icon: XCircle,
    variant: "destructive",
    className: "text-destructive",
  },
  cancelled: {
    label: "Cancelled",
    icon: Ban,
    variant: "outline",
    className: "text-muted-foreground",
  },
};

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function RunRow({ run, projectId }: { run: PipelineRun; projectId: string }) {
  const { cancelRun } = useProjectsStore();
  const [cancelling, setCancelling] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const meta = STATUS_META[run.status];
  const Icon = meta.icon;
  const isLegacy = run.langgraph_run_id.startsWith("legacy-");
  const isActive = run.status === "processing";

  async function handleCancel() {
    setCancelling(true);
    await cancelRun(projectId);
    setCancelling(false);
    setDialogOpen(false);
  }

  return (
    <div className="flex items-start gap-3 border-b border-border py-3">
      <div className="flex flex-col items-center shrink-0 w-10">
        <span className="text-xs font-mono text-muted-foreground">
          #{run.run_number}
        </span>
      </div>
      <Icon
        className={`h-4 w-4 mt-0.5 shrink-0 ${meta.className} ${
          run.status === "processing" ? "animate-spin" : ""
        }`}
      />
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium">{meta.label}</span>
          <Badge variant="outline" className="text-[9px] uppercase">
            {run.trigger_reason}
          </Badge>
          {isLegacy && (
            <Badge
              variant="secondary"
              className="text-[9px] uppercase"
              title="Backfilled from pre-008 schema; run_id is synthetic"
            >
              legacy
            </Badge>
          )}
          {run.final_agent && run.status !== "processing" && (
            <span className="text-[10px] text-muted-foreground">
              final agent: <span className="font-mono">{run.final_agent}</span>
            </span>
          )}
        </div>
        {run.reason && (
          <p className="text-xs text-muted-foreground italic">
            &ldquo;{run.reason}&rdquo;
          </p>
        )}
        {run.error_message && (
          <p className="text-xs text-destructive/80 font-mono truncate">
            {run.error_message}
          </p>
        )}
        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatRelative(run.triggered_at)}
          </span>
          <span>duration: {formatDuration(run.duration_seconds)}</span>
        </div>
      </div>
      {isActive && (
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 shrink-0 text-muted-foreground hover:text-destructive hover:border-destructive/50"
              >
                <Ban className="h-3 w-3" />
                Cancel
              </Button>
            }
          />
          <DialogContent showCloseButton={false}>
            <DialogHeader>
              <DialogTitle>Cancel run #{run.run_number}?</DialogTitle>
              <DialogDescription>
                This will stop the LangGraph run in progress. The project will
                move to a cancelled state and can be rerun later.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
                disabled={cancelling}
              >
                Keep running
              </Button>
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={cancelling}
                className="text-destructive hover:text-destructive"
              >
                {cancelling ? "Cancelling..." : "Cancel run"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

export function RunsTab({ projectId }: { projectId: string }) {
  const { runsByProject, runsLoading, fetchRuns } = useProjectsStore();
  const runs = runsByProject[projectId];

  useEffect(() => {
    fetchRuns(projectId);
  }, [projectId, fetchRuns]);

  if (runs === undefined && runsLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  if (!runs || runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <History className="h-10 w-10 text-muted-foreground/50 mb-3" />
        <p className="text-sm text-muted-foreground">No runs yet</p>
        <p className="text-xs text-muted-foreground">
          Runs appear here once the pipeline has been started at least once.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {runs.map((run) => (
        <RunRow key={run.run_id} run={run} projectId={projectId} />
      ))}
    </div>
  );
}
