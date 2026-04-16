"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useIncidentsStore } from "@/stores/incidents-store";
import { IncidentStatsCards } from "@/components/incidents/incident-stats";
import { IncidentList } from "@/components/incidents/incident-list";
import { IncidentDetailPanel } from "@/components/incidents/incident-detail";
import { IncidentFilters } from "@/components/incidents/incident-filters";
import { cn } from "@/lib/utils";

const POLL_INTERVAL = 30_000;

function useElapsedSeconds(since: Date | null): number {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!since) return;
    setElapsed(Math.floor((Date.now() - since.getTime()) / 1000));
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - since.getTime()) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [since]);
  return elapsed;
}

export default function IncidentsPage() {
  const {
    incidents,
    selectedIncident,
    stats,
    loading,
    detailLoading,
    error,
    lastUpdated,
    fetchAll,
    selectIncident,
  } = useIncidentsStore();

  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);
  const elapsed = useElapsedSeconds(lastUpdated);

  const isStale = lastUpdated != null && elapsed > 60;
  const statusColor = error
    ? "bg-destructive"
    : isStale
      ? "bg-yellow-500"
      : lastUpdated
        ? "bg-green-500"
        : "bg-muted-foreground";
  const showPing = !error && !isStale && lastUpdated != null;

  useEffect(() => {
    fetchAll();
    intervalRef.current = setInterval(fetchAll, POLL_INTERVAL);
    return () => clearInterval(intervalRef.current);
  }, [fetchAll]);

  const activeCount =
    stats?.by_status["active"] ?? incidents.filter((i) => i.status === "active").length;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-3">
          <Link href="/monitoring">
            <Button variant="ghost" size="icon" className="h-7 w-7">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              {showPing && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              )}
              <span
                className={cn(
                  "relative inline-flex h-2.5 w-2.5 rounded-full",
                  statusColor,
                )}
              />
            </span>
            <h1 className="text-lg font-semibold">Incident Records</h1>
            {activeCount > 0 && (
              <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-[10px] font-bold text-destructive-foreground">
                {activeCount}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <IncidentFilters />
          <span className="text-xs text-muted-foreground">
            {lastUpdated && `${elapsed}s ago`}
            {!lastUpdated && loading && "Loading..."}
          </span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mx-6 mt-3 flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-2.5">
          <span className="text-sm text-destructive">{error}</span>
        </div>
      )}

      {/* Stats */}
      <div className="px-6 pt-4 pb-2">
        <IncidentStatsCards stats={stats} loading={loading} />
      </div>

      {/* Master-Detail */}
      <div className="flex flex-1 overflow-hidden border-t">
        {/* Left: incident list */}
        <div className="w-[380px] shrink-0 border-r overflow-hidden">
          <IncidentList
            incidents={incidents}
            selectedId={selectedIncident?.id ?? null}
            loading={loading}
            onSelect={(id) => selectIncident(id)}
          />
        </div>

        {/* Right: detail panel */}
        <div className="flex-1 overflow-hidden">
          <IncidentDetailPanel
            incident={selectedIncident}
            loading={detailLoading}
          />
        </div>
      </div>
    </div>
  );
}
