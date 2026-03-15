"use client";

import { useEffect, useRef, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatsCards } from "@/components/monitoring/stats-cards";
import { DailyChart } from "@/components/monitoring/daily-chart";
import { ConceptsChart } from "@/components/monitoring/concepts-chart";
import { ServiceHealthGrid } from "@/components/monitoring/service-health-grid";
import { AlertsPanel } from "@/components/monitoring/alerts-panel";
import { MetricsPanel } from "@/components/monitoring/metrics-panel";
import { useMonitoringStore } from "@/stores/monitoring-store";
import { cn } from "@/lib/utils";

const POLL_INTERVAL = 15_000;

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

export default function MonitoringPage() {
  const {
    overview,
    daily,
    concepts,
    services,
    alerts,
    metrics,
    loading,
    error,
    lastUpdated,
    fetchAll,
  } = useMonitoringStore();

  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);
  const elapsed = useElapsedSeconds(lastUpdated);

  const isStale = lastUpdated != null && elapsed > 30;
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

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              {showPing && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              )}
              <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", statusColor)} />
            </span>
            <h1 className="text-lg font-semibold">System Monitoring</h1>
          </div>
        </div>
        <span className="text-xs text-muted-foreground">
          {lastUpdated && `Updated ${elapsed}s ago`}
          {!lastUpdated && loading && "Loading..."}
          {!lastUpdated && !loading && "Not connected"}
        </span>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mx-6 mt-3 flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-2.5">
          <span className="text-sm text-destructive">{error}</span>
        </div>
      )}

      {/* Tab Navigation */}
      <Tabs defaultValue="overview" className="flex flex-col flex-1 overflow-hidden">
        <TabsList className="mx-6 mt-3 w-fit">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="alerts">
            Alerts
            {alerts.length > 0 && (
              <span className="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-[10px] font-bold text-destructive-foreground">
                {alerts.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="flex-1 overflow-auto p-6">
          <StatsCards overview={overview} loading={loading} />
          <div className="mt-6">
            <DailyChart daily={daily} loading={loading} />
          </div>
          <div className="mt-6">
            <ConceptsChart concepts={concepts} loading={loading} />
          </div>
        </TabsContent>

        <TabsContent value="services" className="flex-1 overflow-auto p-6">
          <ServiceHealthGrid services={services} loading={loading} />
        </TabsContent>

        <TabsContent value="alerts" className="flex-1 overflow-auto p-6">
          <AlertsPanel alerts={alerts} loading={loading} />
        </TabsContent>

        <TabsContent value="metrics" className="flex-1 overflow-auto p-6">
          <MetricsPanel metrics={metrics} loading={loading} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
