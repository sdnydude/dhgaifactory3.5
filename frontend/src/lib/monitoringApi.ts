import type {
  StatsOverview,
  DailyStats,
  ConceptStats,
  SessionLoggerHealth,
  AlertmanagerAlert,
} from "@/types/monitoring";

const MONITORING_BASE =
  typeof window !== "undefined"
    ? `${window.location.origin}/api/monitoring`
    : "http://localhost:3000/api/monitoring";

const ALERTMANAGER_BASE =
  typeof window !== "undefined"
    ? `${window.location.origin}/api/alertmanager`
    : "http://localhost:3000/api/alertmanager";

const REGISTRY_BASE =
  process.env.NEXT_PUBLIC_REGISTRY_API_URL || "http://localhost:8011";

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchStatsOverview(): Promise<StatsOverview> {
  return fetchJson<StatsOverview>(`${MONITORING_BASE}/sessions/stats/overview`);
}

export async function fetchStatsDaily(): Promise<DailyStats> {
  return fetchJson<DailyStats>(`${MONITORING_BASE}/sessions/stats/daily`);
}

export async function fetchStatsConcepts(): Promise<ConceptStats> {
  return fetchJson<ConceptStats>(
    `${MONITORING_BASE}/sessions/stats/concepts`,
  );
}

export async function fetchSessionLoggerHealth(): Promise<SessionLoggerHealth> {
  return fetchJson<SessionLoggerHealth>(`${MONITORING_BASE}/health`);
}

export async function fetchRegistryHealth(): Promise<string> {
  const response = await fetch(`${REGISTRY_BASE}/healthz`);
  if (!response.ok) throw new Error(`Registry: ${response.status}`);
  return response.text();
}

export async function fetchAlerts(): Promise<AlertmanagerAlert[]> {
  return fetchJson<AlertmanagerAlert[]>(
    `${ALERTMANAGER_BASE}/api/v2/alerts`,
  );
}

export async function fetchMetricsRaw(): Promise<string> {
  const response = await fetch(`${MONITORING_BASE}/metrics`);
  if (!response.ok) throw new Error(`Metrics: ${response.status}`);
  return response.text();
}

export interface TimedHealthResult {
  healthy: boolean;
  responseMs: number;
}

export async function fetchHealthTimed(
  url: string,
): Promise<TimedHealthResult> {
  const start = performance.now();
  try {
    const response = await fetch(url);
    const responseMs = Math.round(performance.now() - start);
    return { healthy: response.ok, responseMs };
  } catch {
    return { healthy: false, responseMs: 0 };
  }
}
