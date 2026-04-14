"use client";

import { useState } from "react";
import { RotateCcw, Square } from "lucide-react";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CMEProjectStatus } from "@/types/cme";
import type { CMEProjectDetail } from "@/types/cme";
import { useProjectsStore } from "@/stores/projects-store";

const CANCELLABLE: CMEProjectStatus[] = [
  CMEProjectStatus.PROCESSING,
  CMEProjectStatus.REVIEW,
];

const RERUNNABLE: CMEProjectStatus[] = [
  CMEProjectStatus.COMPLETE,
  CMEProjectStatus.FAILED,
  CMEProjectStatus.CANCELLED,
  CMEProjectStatus.REVIEW,
];

export function ProjectActionsMenu({ project }: { project: CMEProjectDetail }) {
  const { cancelRun, rerunPipeline } = useProjectsStore();
  const [cancelling, setCancelling] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [rerunReason, setRerunReason] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [rerunOpen, setRerunOpen] = useState(false);

  const canCancel = CANCELLABLE.includes(project.status);
  const canRerun = RERUNNABLE.includes(project.status);

  async function handleCancel() {
    setCancelling(true);
    const run = await cancelRun(project.id);
    setCancelling(false);
    if (run) setCancelOpen(false);
  }

  async function handleRerun() {
    setRerunning(true);
    const run = await rerunPipeline(
      project.id,
      rerunReason.trim() || undefined,
    );
    setRerunning(false);
    if (run) {
      setRerunOpen(false);
      setRerunReason("");
    }
  }

  if (!canCancel && !canRerun) return null;

  return (
    <>
      {canCancel && (
        <Dialog open={cancelOpen} onOpenChange={setCancelOpen}>
          <DialogTrigger
            render={
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-muted-foreground hover:text-destructive hover:border-destructive/50"
              >
                <Square className="h-3 w-3" />
                Cancel
              </Button>
            }
          />
          <DialogContent showCloseButton={false}>
            <DialogHeader>
              <DialogTitle>Cancel running pipeline?</DialogTitle>
              <DialogDescription>
                This stops the current run at agent{" "}
                <strong>{project.current_agent ?? "unknown"}</strong>. Any
                outputs already written are preserved. You can rerun later.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setCancelOpen(false)}
                disabled={cancelling}
              >
                Keep running
              </Button>
              <Button
                variant="destructive"
                onClick={handleCancel}
                disabled={cancelling}
              >
                {cancelling ? "Cancelling..." : "Cancel run"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {canRerun && (
        <Dialog open={rerunOpen} onOpenChange={setRerunOpen}>
          <DialogTrigger
            render={
              <Button variant="outline" size="sm" className="gap-1.5">
                <RotateCcw className="h-3 w-3" />
                Rerun
              </Button>
            }
          />
          <DialogContent showCloseButton={false}>
            <DialogHeader>
              <DialogTitle>Rerun pipeline?</DialogTitle>
              <DialogDescription>
                Starts a new run against the current intake. The existing
                outputs stay in history. You can optionally record why you
                rerun — this shows in the run history.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-2">
              <Label htmlFor="rerun-reason" className="text-xs">
                Reason (optional, 500 chars max)
              </Label>
              <Textarea
                id="rerun-reason"
                value={rerunReason}
                onChange={(e) => setRerunReason(e.target.value.slice(0, 500))}
                placeholder="e.g. Updated disease_state after clinician review"
                rows={3}
              />
              <p className="text-[10px] text-muted-foreground text-right">
                {rerunReason.length}/500
              </p>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setRerunOpen(false)}
                disabled={rerunning}
              >
                Cancel
              </Button>
              <Button onClick={handleRerun} disabled={rerunning}>
                {rerunning ? "Starting..." : "Start rerun"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
