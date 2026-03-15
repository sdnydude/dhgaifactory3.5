"use client";

import type { StatsOverview } from "@/types/monitoring";
import { Skeleton } from "@/components/ui/skeleton";

interface StatsCardsProps {
  overview: StatsOverview | null;
  loading: boolean;
}

interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  accent?: boolean;
}

function StatCard({ label, value, unit, accent }: StatCardProps) {
  return (
    <div
      className={`rounded-lg border bg-card p-5 shadow-sm transition-shadow hover:shadow-md ${
        accent ? "border-l-3 border-l-dhg-orange" : "border-l-3 border-l-primary"
      }`}
    >
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-2 text-3xl font-bold tracking-tight tabular-nums">
        {value}
        {unit && (
          <span className="ml-0.5 text-base font-medium text-muted-foreground">
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}

export function StatsCards({ overview, loading }: StatsCardsProps) {
  if (loading || !overview) {
    return (
      <div className="mb-7 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="mb-7 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
      <StatCard label="Total Sessions" value={overview.total_sessions} />
      <StatCard label="Total Chunks" value={overview.total_chunks} />
      <StatCard label="Total Concepts" value={overview.total_concepts} />
      <StatCard label="Total Edges" value={overview.total_edges} />
      <StatCard
        label="Embedding Coverage"
        value={overview.embedding_coverage_pct}
        unit="%"
        accent
      />
    </div>
  );
}
