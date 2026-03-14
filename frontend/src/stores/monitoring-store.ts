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
      const msg = (e as Error).message;
      console.error("Failed to fetch overview:", msg);
      set({ error: `Session Logger unavailable: ${msg}` });
    }
  },

  fetchServices: async () => {
    try {
      const results = await Promise.all(
        SERVICE_CHECKS.map(async (svc) => {
          const url = svc.useRegistry
            ? `${monitoringApi.REGISTRY_BASE}${svc.url}`
            : svc.url;

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
      const msg = (e as Error).message;
      console.error("Failed to fetch services:", msg);
      set({ error: `Service health check failed: ${msg}` });
    }
  },

  fetchAlerts: async () => {
    try {
      const alerts = await monitoringApi.fetchAlerts();
      set({ alerts });
    } catch (e) {
      const msg = (e as Error).message;
      console.error("Failed to fetch alerts:", msg);
      set({ alerts: [], error: `Alertmanager unavailable: ${msg}` });
    }
  },

  fetchMetrics: async () => {
    try {
      const raw = await monitoringApi.fetchMetricsRaw();
      const metrics = monitoringApi.parsePrometheusMetrics(raw);
      set({ metrics });
    } catch (e) {
      const msg = (e as Error).message;
      console.error("Failed to fetch metrics:", msg);
      set({ error: `Metrics unavailable: ${msg}` });
    }
  },
}));
