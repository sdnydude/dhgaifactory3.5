"use client";

import type { IncidentStats } from "@/lib/incidentsApi";
import { Skeleton } from "@/components/ui/skeleton";

interface IncidentStatsCardsProps {
  stats: IncidentStats | null;
  loading: boolean;
}

function StatCard({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
}) {
  return (
    <div
      className={`rounded-lg border bg-card p-4 shadow-sm ${
        color ?? "border-l-3 border-l-primary"
      }`}
    >
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-1.5 text-2xl font-bold tracking-tight tabular-nums">
        {value}
        {unit && (
          <span className="ml-0.5 text-sm font-medium text-muted-foreground">
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}

function formatMinutes(mins: number | null): string {
  if (mins == null) return "--";
  if (mins < 60) return `${Math.round(mins)}`;
  const h = Math.floor(mins / 60);
  const m = Math.round(mins % 60);
  return `${h}h ${m}m`;
}

export function IncidentStatsCards({ stats, loading }: IncidentStatsCardsProps) {
  if (loading || !stats) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
    );
  }

  const active = stats.by_status["active"] ?? 0;
  const critical = stats.by_severity["critical"] ?? 0;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
      <StatCard label="Total (30d)" value={stats.total} />
      <StatCard
        label="Active"
        value={active}
        color={active > 0 ? "border-l-3 border-l-red-500" : undefined}
      />
      <StatCard
        label="Critical"
        value={critical}
        color={critical > 0 ? "border-l-3 border-l-red-600" : undefined}
      />
      <StatCard
        label="Avg TTD"
        value={formatMinutes(stats.avg_ttd_minutes)}
        unit={stats.avg_ttd_minutes != null && stats.avg_ttd_minutes < 60 ? "min" : ""}
      />
      <StatCard
        label="Avg TTM"
        value={formatMinutes(stats.avg_ttm_minutes)}
        unit={stats.avg_ttm_minutes != null && stats.avg_ttm_minutes < 60 ? "min" : ""}
      />
      <StatCard
        label="Avg TTR"
        value={formatMinutes(stats.avg_ttr_minutes)}
        unit={stats.avg_ttr_minutes != null && stats.avg_ttr_minutes < 60 ? "min" : ""}
      />
    </div>
  );
}
