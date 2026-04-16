"use client";

import {
  X,
  Download,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ChevronUp,
} from "lucide-react";
import { useDownloadsStore } from "@/stores/downloads-store";
import { useDownloadPolling } from "@/hooks/use-download-polling";
import { artifactUrl } from "@/lib/filesApi";
import type { BundleJobResponse } from "@/lib/filesApi";
import { cn } from "@/lib/utils";

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === 0) return "\u2014";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const STATUS_ICON: Record<
  BundleJobResponse["status"],
  React.ReactNode
> = {
  pending: (
    <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
  ),
  running: (
    <Loader2 className="h-3.5 w-3.5 animate-spin text-[color:var(--color-dhg-orange)]" />
  ),
  succeeded: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />,
  failed: <AlertCircle className="h-3.5 w-3.5 text-destructive" />,
};

function JobRow({ job }: { job: BundleJobResponse }) {
  return (
    <li className="flex items-center gap-3 px-4 py-2.5 border-b border-border last:border-b-0">
      {STATUS_ICON[job.status]}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-foreground truncate">
          {job.project_id?.slice(0, 8) ?? "Bundle"} &mdash;{" "}
          {job.scope.replace("_", " ")}
        </p>
        {job.error && (
          <p className="text-[10px] text-destructive truncate mt-0.5">
            {job.error}
          </p>
        )}
      </div>
      <div className="shrink-0 text-right">
        {job.status === "succeeded" ? (
          <a
            href={artifactUrl(job.id)}
            download
            className="inline-flex items-center gap-1 text-xs font-medium text-[color:var(--color-dhg-purple)] hover:underline"
          >
            <Download className="h-3 w-3" />
            {formatBytes(job.artifact_bytes)}
          </a>
        ) : (
          <span className="text-[10px] text-muted-foreground">
            {job.status === "failed" ? "failed" : formatBytes(job.artifact_bytes)}
          </span>
        )}
      </div>
    </li>
  );
}

export function DownloadsTray() {
  useDownloadPolling();

  const jobs = useDownloadsStore((s) => s.jobs);
  const trayOpen = useDownloadsStore((s) => s.trayOpen);
  const closeTray = useDownloadsStore((s) => s.closeTray);
  const toggleTray = useDownloadsStore((s) => s.toggleTray);

  if (jobs.length === 0) return null;

  const activeCount = jobs.filter(
    (j) => j.status === "pending" || j.status === "running",
  ).length;

  if (!trayOpen) {
    return (
      <button
        onClick={toggleTray}
        className={cn(
          "fixed bottom-4 right-4 z-40 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium shadow-lg transition-colors",
          "bg-card border border-border text-foreground hover:bg-muted",
        )}
      >
        <Download className="h-3.5 w-3.5" />
        {activeCount > 0
          ? `${activeCount} downloading\u2026`
          : `${jobs.length} downloads`}
        <ChevronUp className="h-3 w-3" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-40 w-[22rem] rounded-lg border border-border bg-card shadow-xl">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
        <h3 className="text-xs font-semibold text-foreground">
          Downloads
          {activeCount > 0 && (
            <span className="ml-1.5 text-[10px] font-normal text-muted-foreground">
              ({activeCount} active)
            </span>
          )}
        </h3>
        <button
          onClick={closeTray}
          aria-label="Close downloads tray"
          className="h-6 w-6 inline-flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <ul className="max-h-60 overflow-y-auto">
        {jobs.map((job) => (
          <JobRow key={job.id} job={job} />
        ))}
      </ul>
    </div>
  );
}
