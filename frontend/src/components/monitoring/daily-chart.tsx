"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DailyStats } from "@/types/monitoring";
import { Skeleton } from "@/components/ui/skeleton";

interface DailyChartProps {
  daily: DailyStats | null;
  loading: boolean;
}

export function DailyChart({ daily, loading }: DailyChartProps) {
  if (loading || !daily) {
    return (
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <Skeleton className="mb-4 h-5 w-48" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (daily.days.length === 0) {
    return (
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <h3 className="text-sm font-semibold">Sessions Per Day</h3>
        <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
          No session data available
        </div>
      </div>
    );
  }

  const data = daily.days.map((d) => ({
    date: new Date(d.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    sessions: d.session_count,
  }));

  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <h3 className="mb-5 text-sm font-semibold">
        Sessions Per Day
        <span className="ml-2 text-xs font-normal text-muted-foreground">
          Last 7 days
        </span>
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="sessionGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.2} />
              <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="4 4"
            stroke="hsl(var(--border))"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
            width={30}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "8px",
              fontSize: "12px",
            }}
          />
          <Area
            type="monotone"
            dataKey="sessions"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            fill="url(#sessionGradient)"
            dot={{ fill: "hsl(var(--primary))", r: 4 }}
            activeDot={{ fill: "hsl(var(--primary))", r: 6, stroke: "hsl(var(--background))", strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
