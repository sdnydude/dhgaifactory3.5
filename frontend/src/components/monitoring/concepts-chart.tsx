"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { ConceptStats } from "@/types/monitoring";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

interface ConceptsChartProps {
  concepts: ConceptStats | null;
  loading: boolean;
}

const NODE_TYPE_COLORS: Record<string, string> = {
  command: "bg-primary/10 text-primary",
  file_path: "bg-green-500/10 text-green-600 dark:text-green-400",
  error: "bg-destructive/10 text-destructive",
};

export function ConceptsChart({ concepts, loading }: ConceptsChartProps) {
  if (loading || !concepts) {
    return (
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <Skeleton className="mb-4 h-5 w-56" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (concepts.top_concepts.length === 0) {
    return (
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <h3 className="text-sm font-semibold">Top Concepts by Edge Count</h3>
        <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
          No concept data available
        </div>
      </div>
    );
  }

  const data = concepts.top_concepts.map((c) => ({
    name: c.name.length > 20 ? c.name.slice(0, 20) + "..." : c.name,
    fullName: c.name,
    edge_count: c.edge_count,
    node_type: c.node_type,
  }));

  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <h3 className="mb-5 text-sm font-semibold">
        Top Concepts by Edge Count
        <span className="ml-2 text-xs font-normal text-muted-foreground">
          Ranked by connectivity
        </span>
      </h3>
      <ResponsiveContainer width="100%" height={data.length * 40 + 20}>
        <BarChart data={data} layout="vertical" margin={{ left: 80, right: 20 }}>
          <CartesianGrid
            strokeDasharray="4 4"
            stroke="hsl(var(--border))"
            horizontal={false}
          />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12, fill: "hsl(var(--foreground))", fontFamily: "monospace" }}
            axisLine={false}
            tickLine={false}
            width={80}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            formatter={(value, _name, props) => [
              `${value} edges (${(props as { payload: { node_type: string } }).payload.node_type})`,
              "Count",
            ]}
          />
          <Bar dataKey="edge_count" radius={[0, 4, 4, 0]} maxBarSize={28}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill="hsl(var(--primary))"
                className="transition-colors hover:fill-dhg-orange"
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 flex flex-wrap gap-2">
        {concepts.node_type_breakdown.map((t) => (
          <Badge
            key={t.node_type}
            variant="secondary"
            className={NODE_TYPE_COLORS[t.node_type] || ""}
          >
            {t.node_type}: {t.count}
          </Badge>
        ))}
      </div>
    </div>
  );
}
