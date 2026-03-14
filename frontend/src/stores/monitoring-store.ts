"use client";

import { create } from "zustand";
import type {
  StatsOverview,
  DailyStats,
  ConceptStats,
  ServiceHealth,
  AlertmanagerAlert,
  ParsedMetrics,
} from "@/types/monitoring";
import * as monitoringApi from "@/lib/monitoringApi";

interface MonitoringState {
  overview: StatsOverview | null;
  daily: DailyStats | null;
  concepts: ConceptStats | null;
  services: ServiceHealth[];
  alerts: AlertmanagerAlert[];
  metrics: ParsedMetrics | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;

  fetchAll: () => Promise<void>;
  fetchOverview: () => Promise<void>;
  fetchServices: () => Promise<void>;
  fetchAlerts: () => Promise<void>;
  fetchMetrics: () => Promise<void>;
}

function parsePrometheusMetrics(text: string): ParsedMetrics {
  const operations: ParsedMetrics["operations"] = [];
  const opRegex =
    /session_logger_read_operations_total\{operation="([^"]+)"\}\s+([\d.]+)/g;
  let match;
  while ((match = opRegex.exec(text)) !== null) {
    operations.push({ operation: match[1], count: parseFloat(match[2]) });
  }

  // Approximate percentiles from histogram buckets
  const bucketRegex =
    /session_logger_read_latency_bucket\{le="([^"]+)",operation="stats_overview"\}\s+([\d.]+)/g;
  const buckets: { le: number; count: number }[] = [];
  while ((match = bucketRegex.exec(text)) !== null) {
    if (match[1] !== "+Inf") {
      buckets.push({ le: parseFloat(match[1]), count: parseFloat(match[2]) });
    }
  }

  const countMatch = text.match(
    /session_logger_read_latency_count\{operation="stats_overview"\}\s+([\d.]+)/,
  );
  const totalCount = countMatch ? parseFloat(countMatch[1]) : 0;

  function percentile(p: number): number {
    if (totalCount === 0 || buckets.length === 0) return 0;
    const target = totalCount * p;
    for (const b of buckets) {
      if (b.count >= target) return b.le;
    }
    return buckets[buckets.length - 1]?.le ?? 0;
  }

  const errorRegex = /session_logger_errors_total\{[^}]*\}\s+([\d.]+)/g;
  let totalErrors = 0;
  while ((match = errorRegex.exec(text)) !== null) {
    totalErrors += parseFloat(match[1]);
  }

  return {
    operations,
    latency: { p50: percentile(0.5), p95: percentile(0.95), p99: percentile(0.99) },
    totalErrors,
  };
}

const SERVICE_CHECKS = [
  { name: "Session Logger", port: 8009, url: "/api/monitoring/health", description: "Session tracking & stats" },
  { name: "Registry API", port: 8011, url: "/healthz", description: "FastAPI data registry", useRegistry: true },
  { name: "Prometheus", port: 9090, url: "http://localhost:9090/-/healthy", description: "Metrics collection", direct: true },
  { name: "Grafana", port: 3001, url: "http://localhost:3001/api/health", description: "Dashboard visualization", direct: true },
  { name: "Ollama", port: 11434, url: "http://localhost:11434/", description: "Local LLM inference", direct: true },
];

export const useMonitoringStore = create<MonitoringState>((set) => ({
  overview: null,
  daily: null,
  concepts: null,
  services: [],
  alerts: [],
  metrics: null,
  loading: false,
  error: null,
  lastUpdated: null,

  fetchAll: async () => {
    set({ loading: true, error: null });
    try {
      const store = useMonitoringStore.getState();
      await Promise.all([
        store.fetchOverview(),
        store.fetchServices(),
        store.fetchAlerts(),
        store.fetchMetrics(),
      ]);
      set({ loading: false, lastUpdated: new Date() });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchOverview: async () => {
    try {
      const [overview, daily, concepts] = await Promise.all([
        monitoringApi.fetchStatsOverview(),
        monitoringApi.fetchStatsDaily(),
        monitoringApi.fetchStatsConcepts(),
      ]);
      set({ overview, daily, concepts });
    } catch (e) {
      console.error("Failed to fetch overview:", e);
    }
  },

  fetchServices: async () => {
    try {
      const results = await Promise.all(
        SERVICE_CHECKS.map(async (svc) => {
          let url = svc.url;
          if (svc.useRegistry) {
            const registryBase =
              process.env.NEXT_PUBLIC_REGISTRY_API_URL || "http://localhost:8011";
            url = `${registryBase}${svc.url}`;
          } else if (!svc.direct) {
            url = svc.url;
          }

          const { healthy, responseMs } = await monitoringApi.fetchHealthTimed(url);

          return {
            name: svc.name,
            port: svc.port,
            status: healthy ? "healthy" : "down",
            responseMs,
            description: svc.description,
          } as ServiceHealth;
        }),
      );
      set({ services: results });
    } catch (e) {
      console.error("Failed to fetch services:", e);
    }
  },

  fetchAlerts: async () => {
    try {
      const alerts = await monitoringApi.fetchAlerts();
      set({ alerts });
    } catch (e) {
      console.error("Failed to fetch alerts:", e);
      set({ alerts: [] });
    }
  },

  fetchMetrics: async () => {
    try {
      const raw = await monitoringApi.fetchMetricsRaw();
      const metrics = parsePrometheusMetrics(raw);
      set({ metrics });
    } catch (e) {
      console.error("Failed to fetch metrics:", e);
    }
  },
}));
