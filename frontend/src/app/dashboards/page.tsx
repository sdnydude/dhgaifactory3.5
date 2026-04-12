"use client";

import { BarChart3, ExternalLink } from "lucide-react";

const DASHBOARDS = [
  {
    name: "Core Golden Signals",
    description: "Request rate, error rate, latency, and saturation across all services",
    url: "http://10.0.0.251:3001/d/core-golden-signals",
  },
  {
    name: "Docker Overview",
    description: "Container CPU, memory, network, and disk I/O metrics",
    url: "http://10.0.0.251:3001/d/docker-overview",
  },
  {
    name: "LangGraph Agent Performance",
    description: "Agent execution times, token usage, and success rates",
    url: "http://10.0.0.251:3001",
  },
  {
    name: "PostgreSQL Metrics",
    description: "Connection pools, query performance, replication lag, and table stats",
    url: "http://10.0.0.251:3001",
  },
];

export default function DashboardsPage() {
  return (
    <div className="flex flex-col h-full overflow-auto">
      <div className="border-b px-6 py-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Dashboards</h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Grafana dashboards for system observability
        </p>
      </div>

      <div className="p-6 grid grid-cols-2 gap-4">
        {DASHBOARDS.map((d) => (
          <a
            key={d.name}
            href={d.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group rounded-lg border border-border p-4 hover:border-primary/50 hover:bg-muted/50 transition-colors"
          >
            <div className="flex items-start justify-between">
              <h3 className="text-sm font-medium">{d.name}</h3>
              <ExternalLink className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
              {d.description}
            </p>
          </a>
        ))}
      </div>
    </div>
  );
}
