"use client";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { IncidentListItem, Severity, IncidentStatus } from "@/lib/incidentsApi";
import { SEVERITY_COLORS, STATUS_COLORS } from "@/lib/incidentsApi";

interface IncidentListProps {
  incidents: IncidentListItem[];
  selectedId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function IncidentList({
  incidents,
  selectedId,
  loading,
  onSelect,
}: IncidentListProps) {
  if (loading && incidents.length === 0) {
    return (
      <div className="flex flex-col gap-2 p-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-lg" />
        ))}
      </div>
    );
  }

  if (incidents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="mb-3 text-4xl opacity-30">&#10003;</div>
        <p className="text-sm text-muted-foreground">No incidents found</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-1 p-2">
        {incidents.map((inc) => (
          <button
            key={inc.id}
            onClick={() => onSelect(inc.id)}
            className={cn(
              "flex flex-col gap-1.5 rounded-lg border px-3 py-2.5 text-left transition-colors",
              selectedId === inc.id
                ? "border-primary bg-primary/5"
                : "border-transparent hover:bg-muted/50",
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm font-medium leading-tight line-clamp-2">
                {inc.title}
              </span>
              <Badge
                className={cn(
                  "shrink-0 text-[10px] font-bold uppercase",
                  SEVERITY_COLORS[inc.severity as Severity],
                )}
              >
                {inc.severity}
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <Badge
                variant="outline"
                className={cn(
                  "h-5 text-[10px] font-medium",
                  STATUS_COLORS[inc.status as IncidentStatus],
                )}
              >
                {inc.status}
              </Badge>
              <span>{inc.category}</span>
              <span className="ml-auto">{timeAgo(inc.detected_at)}</span>
            </div>
            {inc.affected_services.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {inc.affected_services.slice(0, 3).map((svc) => (
                  <span
                    key={svc}
                    className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground"
                  >
                    {svc}
                  </span>
                ))}
                {inc.affected_services.length > 3 && (
                  <span className="text-[10px] text-muted-foreground">
                    +{inc.affected_services.length - 3}
                  </span>
                )}
              </div>
            )}
          </button>
        ))}
      </div>
    </ScrollArea>
  );
}
