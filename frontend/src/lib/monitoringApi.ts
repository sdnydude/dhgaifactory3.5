import type {
  StatsOverview,
  DailyStats,
  ConceptStats,
  SessionLoggerHealth,
  AlertmanagerAlert,
  ParsedMetrics,
} from "@/types/monitoring";

const MONITORING_BASE =
  typeof window !== "undefined"
    ? `${window.location.origin}/api/monitoring`
    : "http://localhost:3000/api/monitoring";

const ALERTMANAGER_BASE =
  typeof window !== "undefined"
    ? `${window.location.origin}/api/alertmanager`
    : "http://localhost:3000/api/alertmanager";

export const REGISTRY_BASE = "/api/registry";

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

export function parsePrometheusMetrics(text: string): ParsedMetrics {
  const operations: ParsedMetrics["operations"] = [];
  const opRegex =
    /session_logger_read_operations_total\{operation="([^"]+)"\}\s+([\d.]+)/g;
  let match;
  while ((match = opRegex.exec(text)) !== null) {
    operations.push({ operation: match[1], count: parseFloat(match[2]) });
  }

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
