import type {
  PromVectorResult,
  PromMatrixResult,
  PromTarget,
  CmePipelineStats,
  CmeServiceStats,
  CorrectionStats,
  FeedbackLoopHealth,
  DeferredItemStats,
  IncidentStats,
  Telemetry,
} from "./types";

// ── Constants ──────────────────────────────────────────────────────────────

export const POLL_MS = 10_000;
export const RANGE_WINDOW_SECONDS = 15 * 60;
export const RANGE_STEP_SECONDS = 30;

// The registry's own Postgres, as labelled by the postgres_exporter multi-target
// scrape. Other services (portage, medkb, …) share the same metric names.
export const PG_REGISTRY_SELECTOR = '{service="registry-db"}';

export const BORDERED_ROW =
  "flex items-baseline justify-between py-1 border-b border-[color:var(--mc-frame)]/40";

export const EMPTY: Telemetry = {
  targets: null,
  targetsTotal: null,
  targetsDown: null,
  alertsFiring: null,
  regReqRate: null,
  regErrRate: null,
  regLatencyP95: null,
  pgConnections: null,
  pgCacheHit: null,
  pgUp: null,
  nodeLoad1: null,
  nodeMemAvailPct: null,
  promUptime: null,
  containersRunning: null,
  containerCpuCores: null,
  containerMemBytes: null,
  incidentStats: null,
  cmePipeline: null,
  cmeServices: null,
  regReqRateSpark: [],
  regLatencySpark: [],
  nodeLoadSpark: [],
  correctionStats: null,
  feedbackHealth: null,
  deferredStats: null,
  lastUpdated: null,
  reachable: true,
};

// ── Fetch helpers ──────────────────────────────────────────────────────────

export async function promQuery<T = PromVectorResult[]>(
  query: string,
): Promise<T | null> {
  try {
    const r = await fetch(
      `/api/prometheus/api/v1/query?query=${encodeURIComponent(query)}`,
      { cache: "no-store" },
    );
    if (!r.ok) {
      console.warn(`[dashboard] promQuery ${query} returned ${r.status}`);
      return null;
    }
    const j = await r.json();
    if (j.status !== "success") {
      console.warn(`[dashboard] promQuery ${query} status: ${j.status}`);
      return null;
    }
    return j.data.result as T;
  } catch (err) {
    console.warn(`[dashboard] promQuery ${query} failed:`, err);
    return null;
  }
}

export async function promRange(
  query: string,
): Promise<PromMatrixResult[] | null> {
  try {
    const end = Math.floor(Date.now() / 1000);
    const start = end - RANGE_WINDOW_SECONDS;
    const r = await fetch(
      `/api/prometheus/api/v1/query_range?query=${encodeURIComponent(query)}&start=${start}&end=${end}&step=${RANGE_STEP_SECONDS}`,
      { cache: "no-store" },
    );
    if (!r.ok) {
      console.warn(`[dashboard] promRange ${query} returned ${r.status}`);
      return null;
    }
    const j = await r.json();
    if (j.status !== "success") {
      console.warn(`[dashboard] promRange ${query} status: ${j.status}`);
      return null;
    }
    return j.data.result as PromMatrixResult[];
  } catch (err) {
    console.warn(`[dashboard] promRange ${query} failed:`, err);
    return null;
  }
}

export async function fetchTargets(): Promise<PromTarget[] | null> {
  try {
    const r = await fetch(
      "/api/prometheus/api/v1/targets?state=active",
      { cache: "no-store" },
    );
    if (!r.ok) {
      console.warn(`[dashboard] fetchTargets returned ${r.status}`);
      return null;
    }
    const j = await r.json();
    return j.data.activeTargets as PromTarget[];
  } catch (err) {
    console.warn("[dashboard] fetchTargets failed:", err);
    return null;
  }
}

export async function fetchAlerts(): Promise<number | null> {
  try {
    const r = await fetch("/api/alertmanager/api/v2/alerts", {
      cache: "no-store",
    });
    if (!r.ok) {
      console.warn(`[dashboard] fetchAlerts returned ${r.status}`);
      return null;
    }
    const j = (await r.json()) as { status: { state: string } }[];
    return j.filter((a) => a.status?.state === "active").length;
  } catch (err) {
    console.warn("[dashboard] fetchAlerts failed:", err);
    return null;
  }
}

export async function fetchRegistryJson<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`/api/registry${path}`, { cache: "no-store" });
    if (!r.ok) {
      console.warn(`[dashboard] registry ${path} returned ${r.status}`);
      return null;
    }
    return (await r.json()) as T;
  } catch (err) {
    console.warn(`[dashboard] registry ${path} fetch failed:`, err);
    return null;
  }
}

// ── Data transform helpers ─────────────────────────────────────────────────

export function firstSample(result: PromVectorResult[] | null): number | null {
  if (!result || result.length === 0) return null;
  const v = parseFloat(result[0].value[1]);
  return Number.isFinite(v) ? v : null;
}

export function toSpark(matrix: PromMatrixResult[] | null): { v: number }[] {
  if (!matrix || matrix.length === 0) return [];
  return matrix[0].values
    .map(([, val]) => ({ v: parseFloat(val) }))
    .filter((p) => Number.isFinite(p.v));
}

// ── Format helpers ─────────────────────────────────────────────────────────

export function formatNumber(
  n: number | null,
  opts: { decimals?: number; unit?: string; ifNull?: string } = {},
): string {
  if (n === null || !Number.isFinite(n)) return opts.ifNull ?? "——";
  const { decimals = 0, unit = "" } = opts;
  return `${n.toFixed(decimals)}${unit}`;
}

export function formatPercent(n: number | null, decimals = 1): string {
  if (n === null || !Number.isFinite(n)) return "——";
  return `${(n * 100).toFixed(decimals)}%`;
}

export function formatBytes(bytes: number | null): string {
  if (bytes === null || !Number.isFinite(bytes)) return "——";
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let v = bytes;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function formatUptime(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return "——";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function statusTone(status: string): string {
  switch (status) {
    case "review": return "mc-warn";
    case "failed": return "mc-bad";
    case "processing": return "mc-info";
    default: return "mc-ok";
  }
}

export function qualityTone(score: number | null): string {
  if (score === null) return "mc-cell";
  if (score >= 0.8) return "mc-ok";
  if (score >= 0.5) return "mc-warn";
  return "mc-bad";
}

// ── Main fetch orchestrator ────────────────────────────────────────────────

export async function fetchTelemetry(): Promise<Telemetry> {
  const [
    targets,
    targetsTotal,
    targetsDown,
    alertsFiring,
    regReq,
    regErr,
    regLat,
    pgConn,
    pgHit,
    pgUp,
    nodeLoad,
    nodeMem,
    promUp,
    cAdvisorCount,
    cAdvisorCpu,
    cAdvisorMem,
    regReqMatrix,
    regLatMatrix,
    loadMatrix,
    cmePipelineRaw,
    cmeServicesRaw,
    correctionStatsRaw,
    feedbackHealthRaw,
    deferredStatsRaw,
    incidentStatsRaw,
  ] = await Promise.all([
    fetchTargets(),
    promQuery("count(up)"),
    promQuery("count(up == 0) or vector(0)"),
    fetchAlerts(),
    promQuery('sum(rate(http_requests_total{job="registry-api"}[1m]))'),
    promQuery(
      'sum(rate(http_requests_total{job="registry-api",status=~"5.."}[5m])) / clamp_min(sum(rate(http_requests_total{job="registry-api"}[5m])),1)',
    ),
    promQuery(
      'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="registry-api"}[5m])))',
    ),
    promQuery(`sum(pg_stat_activity_count${PG_REGISTRY_SELECTOR})`),
    promQuery(
      `sum(pg_stat_database_blks_hit${PG_REGISTRY_SELECTOR}) / clamp_min(sum(pg_stat_database_blks_hit${PG_REGISTRY_SELECTOR} + pg_stat_database_blks_read${PG_REGISTRY_SELECTOR}), 1)`,
    ),
    promQuery('max(up{job="postgres",service="registry-db"})'),
    promQuery('node_load1{job="node-exporter"}'),
    promQuery(
      'avg(node_memory_MemAvailable_bytes{job="node-exporter"}) / avg(node_memory_MemTotal_bytes{job="node-exporter"})',
    ),
    promQuery(
      'time() - process_start_time_seconds{job="prometheus"}',
    ),
    promQuery(
      'count(count by (name) (container_last_seen{job="cadvisor",name!=""}))',
    ),
    promQuery(
      'sum(rate(container_cpu_usage_seconds_total{job="cadvisor",name!=""}[5m]))',
    ),
    promQuery(
      'sum(container_memory_working_set_bytes{job="cadvisor",name!=""})',
    ),
    promRange('sum(rate(http_requests_total{job="registry-api"}[1m]))'),
    promRange(
      'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="registry-api"}[5m])))',
    ),
    promRange('node_load1{job="node-exporter"}'),
    fetchRegistryJson<CmePipelineStats>("/api/cme/stats/pipeline"),
    fetchRegistryJson<CmeServiceStats>("/api/cme/stats/services"),
    fetchRegistryJson<CorrectionStats>("/api/corrections/stats"),
    fetchRegistryJson<FeedbackLoopHealth>("/api/feedback-loop/health"),
    fetchRegistryJson<DeferredItemStats>("/api/deferred-items/stats"),
    fetchRegistryJson<IncidentStats>("/api/incidents/stats"),
  ]);

  const reachable = targets !== null;

  return {
    targets,
    targetsTotal: firstSample(targetsTotal),
    targetsDown: firstSample(targetsDown),
    alertsFiring,
    regReqRate: firstSample(regReq),
    regErrRate: firstSample(regErr),
    regLatencyP95: firstSample(regLat),
    pgConnections: firstSample(pgConn),
    pgCacheHit: firstSample(pgHit),
    pgUp: firstSample(pgUp),
    nodeLoad1: firstSample(nodeLoad),
    nodeMemAvailPct: firstSample(nodeMem),
    promUptime: firstSample(promUp),
    containersRunning: firstSample(cAdvisorCount),
    containerCpuCores: firstSample(cAdvisorCpu),
    containerMemBytes: firstSample(cAdvisorMem),
    incidentStats: incidentStatsRaw,
    cmePipeline: cmePipelineRaw,
    cmeServices: cmeServicesRaw,
    regReqRateSpark: toSpark(regReqMatrix),
    regLatencySpark: toSpark(regLatMatrix),
    nodeLoadSpark: toSpark(loadMatrix),
    correctionStats: correctionStatsRaw,
    feedbackHealth: feedbackHealthRaw,
    deferredStats: deferredStatsRaw,
    lastUpdated: new Date(),
    reachable,
  };
}
