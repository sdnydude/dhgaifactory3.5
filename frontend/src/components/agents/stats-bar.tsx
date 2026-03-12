"use client";

import { Activity, CheckCircle2, XCircle, Pause, Clock, Layers } from "lucide-react";
import type { AgentStats } from "@/lib/agentsApi";

interface StatsBarProps {
  stats: AgentStats | null;
}

const items = [
  { key: "totalThreads" as const, label: "Total Threads", icon: Layers, color: "text-foreground" },
  { key: "running" as const, label: "Running", icon: Activity, color: "text-dhg-orange" },
  { key: "interrupted" as const, label: "Awaiting Review", icon: Pause, color: "text-yellow-500" },
  { key: "completed" as const, label: "Completed", icon: CheckCircle2, color: "text-green-500" },
  { key: "failed" as const, label: "Failed", icon: XCircle, color: "text-destructive" },
  { key: "idle" as const, label: "Idle", icon: Clock, color: "text-muted-foreground" },
];

export function StatsBar({ stats }: StatsBarProps) {
  return (
    <div className="grid grid-cols-6 gap-3 p-4 border-b border-border">
      {items.map(({ key, label, icon: Icon, color }) => (
        <div key={key} className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-muted/50">
          <Icon className={`h-4 w-4 shrink-0 ${color}`} />
          <div className="min-w-0">
            <p className="text-lg font-semibold leading-tight tabular-nums">
              {stats ? stats[key] : "—"}
            </p>
            <p className="text-[10px] text-muted-foreground truncate">{label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
