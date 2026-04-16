"use client";

import { cn } from "@/lib/utils";

interface SnapshotDashboardProps {
  snapshot: Record<string, unknown>;
}

/* ── Typed sub-structures ─────────────────────────────────── */

interface HostMetrics {
  memory_total_gb?: number;
  memory_used_gb?: number;
  memory_percent?: number;
  swap_total_gb?: number;
  swap_used_gb?: number;
  swap_percent?: number;
  load_avg_1m?: number;
  error?: string;
}

interface DbMetrics {
  total_connections?: number;
  active?: number;
  idle?: number;
  idle_in_transaction?: number;
}

interface ContainerInfo {
  name: string;
  status: string;
}

/* ── Small sub-components ─────────────────────────────────── */

function GaugeBar({
  label,
  value,
  max,
  unit,
  percent,
}: {
  label: string;
  value: number;
  max: number;
  unit: string;
  percent: number;
}) {
  const color =
    percent >= 90
      ? "bg-red-500"
      : percent >= 75
        ? "bg-orange-500"
        : percent >= 50
          ? "bg-yellow-500"
          : "bg-green-500";

  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[11px] text-muted-foreground">{label}</span>
        <span className="text-sm font-medium tabular-nums">
          {value} / {max} {unit}
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      <div className="text-right mt-0.5">
        <span
          className={cn(
            "text-[10px] font-medium",
            percent >= 90
              ? "text-red-600 dark:text-red-400"
              : percent >= 75
                ? "text-orange-600 dark:text-orange-400"
                : "text-muted-foreground",
          )}
        >
          {percent.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  sub,
  alert,
}: {
  label: string;
  value: string | number;
  sub?: string;
  alert?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border p-3 text-center",
        alert
          ? "border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-900/20"
          : "bg-card",
      )}
    >
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
        {label}
      </div>
      <div
        className={cn(
          "text-lg font-semibold tabular-nums",
          alert ? "text-red-600 dark:text-red-400" : "",
        )}
      >
        {value}
      </div>
      {sub && (
        <div className="text-[10px] text-muted-foreground mt-0.5">{sub}</div>
      )}
    </div>
  );
}

/* ── Main component ───────────────────────────────────────── */

export function SnapshotDashboard({ snapshot }: SnapshotDashboardProps) {
  const host = (snapshot.host ?? {}) as HostMetrics;
  const db = (snapshot.database ?? {}) as DbMetrics;
  const containers = (snapshot.containers ?? []) as ContainerInfo[];
  const capturedAt = snapshot.captured_at as string | undefined;

  const hasHost = host && !host.error && host.memory_total_gb !== undefined;
  const hasDb = db && db.total_connections !== undefined;

  return (
    <div className="space-y-4">
      {/* Captured timestamp */}
      {capturedAt && (
        <div className="text-[10px] text-muted-foreground text-right">
          Captured: {new Date(capturedAt).toLocaleString()}
        </div>
      )}

      {/* Host metrics */}
      {hasHost && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
            Host Resources
          </h3>

          {/* Load + summary cards */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <MetricCard
              label="Load (1m)"
              value={host.load_avg_1m?.toFixed(2) ?? "--"}
            />
            <MetricCard
              label="RAM Used"
              value={`${host.memory_used_gb}G`}
              sub={`of ${host.memory_total_gb}G`}
              alert={(host.memory_percent ?? 0) >= 90}
            />
            <MetricCard
              label="Swap Used"
              value={`${host.swap_used_gb}G`}
              sub={`of ${host.swap_total_gb}G`}
              alert={(host.swap_percent ?? 0) >= 80}
            />
          </div>

          {/* Gauge bars */}
          <div className="space-y-3">
            <GaugeBar
              label="Memory"
              value={host.memory_used_gb ?? 0}
              max={host.memory_total_gb ?? 1}
              unit="GB"
              percent={host.memory_percent ?? 0}
            />
            <GaugeBar
              label="Swap"
              value={host.swap_used_gb ?? 0}
              max={host.swap_total_gb ?? 1}
              unit="GB"
              percent={host.swap_percent ?? 0}
            />
          </div>
        </div>
      )}

      {/* Host error */}
      {host.error && (
        <div className="rounded-lg border border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-900/20 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-red-600 dark:text-red-400 mb-1">
            Host Metrics Unavailable
          </h3>
          <p className="text-sm text-red-600 dark:text-red-400">{host.error}</p>
        </div>
      )}

      {/* Database connection pool */}
      {hasDb && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
            Database Connections
          </h3>
          <div className="grid grid-cols-4 gap-2">
            <MetricCard label="Total" value={db.total_connections ?? 0} />
            <MetricCard
              label="Active"
              value={db.active ?? 0}
              alert={(db.active ?? 0) > 10}
            />
            <MetricCard label="Idle" value={db.idle ?? 0} />
            <MetricCard
              label="Idle in Txn"
              value={db.idle_in_transaction ?? 0}
              alert={(db.idle_in_transaction ?? 0) > 0}
            />
          </div>
        </div>
      )}

      {/* Container list */}
      {containers.length > 0 && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
            Containers ({containers.length})
          </h3>
          <div className="space-y-1.5">
            {containers.map((c) => {
              const healthy = c.status.toLowerCase().includes("healthy");
              const up = c.status.toLowerCase().includes("up");
              return (
                <div
                  key={c.name}
                  className="flex items-center justify-between rounded border px-3 py-1.5"
                >
                  <span className="text-[11px] font-mono">{c.name}</span>
                  <span
                    className={cn(
                      "text-[10px] font-medium",
                      healthy
                        ? "text-green-600 dark:text-green-400"
                        : up
                          ? "text-yellow-600 dark:text-yellow-400"
                          : "text-red-600 dark:text-red-400",
                    )}
                  >
                    {c.status}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
