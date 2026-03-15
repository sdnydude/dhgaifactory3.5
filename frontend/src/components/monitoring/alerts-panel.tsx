"use client";

import type { AlertmanagerAlert } from "@/types/monitoring";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface AlertsPanelProps {
  alerts: AlertmanagerAlert[];
  loading: boolean;
}

const severityStyles: Record<string, string> = {
  critical: "bg-destructive/10 text-destructive",
  warning: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400",
  info: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function AlertsPanel({ alerts, loading }: AlertsPanelProps) {
  if (loading) {
    return (
      <div className="flex flex-col gap-3.5">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border bg-card py-16 shadow-sm">
        <div className="mb-3 text-4xl opacity-30">&#10003;</div>
        <p className="text-sm text-muted-foreground">No active alerts</p>
      </div>
    );
  }

  const sorted = [...alerts].sort((a, b) => {
    const severityOrder: Record<string, number> = {
      critical: 0,
      warning: 1,
      info: 2,
    };
    const aOrder = severityOrder[a.labels.severity] ?? 3;
    const bOrder = severityOrder[b.labels.severity] ?? 3;
    if (aOrder !== bOrder) return aOrder - bOrder;
    return new Date(b.startsAt).getTime() - new Date(a.startsAt).getTime();
  });

  return (
    <div className="flex flex-col gap-3.5">
      {sorted.map((alert, i) => {
        const severity = alert.labels.severity || "warning";
        const style = severityStyles[severity] || severityStyles.info;
        const alertName = alert.labels.alertname || "Unknown Alert";
        const description =
          alert.annotations.description ||
          alert.annotations.summary ||
          "No description available";
        const labels = Object.entries(alert.labels)
          .filter(([k]) => k !== "alertname" && k !== "severity")
          .map(([k, v]) => `${k}=${v}`)
          .join(", ");

        return (
          <div
            key={`${alertName}-${i}`}
            className="flex gap-4 rounded-xl border bg-card p-5 shadow-sm"
          >
            <Badge
              variant="secondary"
              className={`mt-0.5 h-fit shrink-0 text-[10px] font-bold uppercase tracking-wider ${style}`}
            >
              {severity}
            </Badge>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">{alertName}</div>
              <div className="mt-1 break-words text-[13px] leading-relaxed text-muted-foreground">
                {description}
              </div>
              <div className="mt-2 break-all font-mono text-[11px] text-muted-foreground/70">
                Fired {timeAgo(alert.startsAt)}
                {labels && ` · ${labels}`}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
