"use client";

import type { ParsedMetrics } from "@/types/monitoring";
import { Skeleton } from "@/components/ui/skeleton";

interface MetricsPanelProps {
  metrics: ParsedMetrics | null;
  loading: boolean;
}

function GaugeBar({ label, value, maxMs }: { label: string; value: number; maxMs: number }) {
  const pct = Math.min((value / maxMs) * 100, 100);
  return (
    <div className="mb-3.5 flex items-center gap-3.5">
      <span className="w-10 text-right font-mono text-xs font-semibold text-muted-foreground">
        {label}
      </span>
      <div className="flex-1 overflow-hidden rounded-md bg-muted h-5">
        <div
          className="flex h-full items-center justify-end rounded-md bg-primary px-2 transition-all duration-700"
          style={{ width: `${Math.max(pct, 8)}%` }}
        >
          <span className="font-mono text-[11px] font-semibold text-primary-foreground">
            {value}ms
          </span>
        </div>
      </div>
    </div>
  );
}

export function MetricsPanel({ metrics, loading }: MetricsPanelProps) {
  if (loading) {
    return (
      <div className="flex flex-col gap-5">
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex items-center justify-center rounded-xl border bg-card py-16 shadow-sm">
        <p className="text-sm text-muted-foreground">No metrics collected yet</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Operation Counters */}
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          Operation Counters
        </h3>
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
          {metrics.operations.length > 0 ? (
            metrics.operations.map((op) => (
              <div key={op.operation} className="rounded-lg bg-muted p-4 text-center">
                <div className="font-mono text-[11px] font-medium text-muted-foreground">
                  {op.operation}
                </div>
                <div className="mt-1.5 font-mono text-2xl font-bold tabular-nums">
                  {op.count}
                </div>
                <div className="mt-0.5 text-[11px] text-muted-foreground">requests</div>
              </div>
            ))
          ) : (
            <div className="col-span-3 py-4 text-center text-sm text-muted-foreground">
              No operations recorded yet
            </div>
          )}
        </div>
      </div>

      {/* Latency Percentiles */}
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          Read Latency Percentiles
        </h3>
        <GaugeBar label="p50" value={metrics.latency.p50} maxMs={50} />
        <GaugeBar label="p95" value={metrics.latency.p95} maxMs={50} />
        <GaugeBar label="p99" value={metrics.latency.p99} maxMs={50} />
      </div>

      {/* Error Rate */}
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          Error Rate
        </h3>
        {metrics.totalErrors === 0 ? (
          <div className="flex items-center gap-3 rounded-lg border border-green-500/15 bg-green-500/5 p-4">
            <span className="font-mono text-3xl font-bold text-green-500">0</span>
            <div className="text-sm">
              <span className="block font-semibold">No errors recorded</span>
              <span className="text-muted-foreground">
                All session-logger operations completing successfully
              </span>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-lg border border-destructive/15 bg-destructive/5 p-4">
            <span className="font-mono text-3xl font-bold text-destructive">
              {metrics.totalErrors}
            </span>
            <div className="text-sm">
              <span className="block font-semibold">Errors detected</span>
              <span className="text-muted-foreground">
                Check session-logger logs for details
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
