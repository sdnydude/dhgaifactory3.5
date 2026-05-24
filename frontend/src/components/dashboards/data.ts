import type {
  PromVectorResult,
  PromMatrixResult,
  PromTarget,
  CmePipelineStats,
  CmeServiceStats,
  LgTopNode,
  Telemetry,
} from "./types";

// ── Constants ──────────────────────────────────────────────────────────────

export const POLL_MS = 10_000;
export const RANGE_WINDOW_SECONDS = 15 * 60;
export const RANGE_STEP_SECONDS = 30;
export const LG_SERVICE_SELECTOR = '{service="dhg-langgraph-agents"}';

export const BORDERED_ROW =
  "flex items-baseline justify-between py-1 border-b border-[color:var(--mc-frame)]/40";

export const EMPTY: Telemetry = {
  targets: null,
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
  lgCalls15m: null,
  lgLatencyP95: null,
  lgActiveNodes: null,
  lgTopNodes: null,
  lgCallsSpark: [],
  cmePipeline: null,
  cmeServices: null,
  regReqRateSpark: [],
  regLatencySpark: [],
  nodeLoadSpark: [],
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
    lgCalls,
    lgLat,
    lgNodes,
    lgTop,
    regReqMatrix,
    regLatMatrix,
    loadMatrix,
    lgCallsMatrix,
    cmePipelineRaw,
    cmeServicesRaw,
  ] = await Promise.all([
    fetchTargets(),
    fetchAlerts(),
    promQuery('sum(rate(http_requests_total{job="registry-api"}[1m]))'),
    promQuery(
      'sum(rate(http_requests_total{job="registry-api",status=~"5.."}[5m])) / clamp_min(sum(rate(http_requests_total{job="registry-api"}[5m])),1)',
    ),
    promQuery(
      'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="registry-api"}[5m])))',
    ),
    promQuery("pg_stat_activity_count"),
    promQuery(
      "sum(pg_stat_database_blks_hit) / clamp_min(sum(pg_stat_database_blks_hit + pg_stat_database_blks_read), 1)",
    ),
    promQuery('up{job="postgres"}'),
    promQuery("node_load1"),
    promQuery(
      "avg(node_memory_MemAvailable_bytes) / avg(node_memory_MemTotal_bytes)",
    ),
    promQuery(
      'time() - process_start_time_seconds{job="prometheus"}',
    ),
    promQuery(
      `sum(increase(traces_spanmetrics_calls_total${LG_SERVICE_SELECTOR}[15m]))`,
    ),
    promQuery(
      `histogram_quantile(0.95, sum by (le) (rate(traces_spanmetrics_latency_bucket${LG_SERVICE_SELECTOR}[5m])))`,
    ),
    promQuery(
      `count(count by (span_name) (traces_spanmetrics_calls_total${LG_SERVICE_SELECTOR}))`,
    ),
    promQuery(
      `topk(8, sum by (span_name) (increase(traces_spanmetrics_calls_total${LG_SERVICE_SELECTOR}[15m])))`,
    ),
    promRange('sum(rate(http_requests_total{job="registry-api"}[1m]))'),
    promRange(
      'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="registry-api"}[5m])))',
    ),
    promRange("node_load1"),
    promRange(
      `sum(rate(traces_spanmetrics_calls_total${LG_SERVICE_SELECTOR}[1m]))`,
    ),
    fetchRegistryJson<CmePipelineStats>("/api/cme/stats/pipeline"),
    fetchRegistryJson<CmeServiceStats>("/api/cme/stats/services"),
  ]);

  const reachable = targets !== null;

  const lgTopNodes: LgTopNode[] | null =
    lgTop === null
      ? null
      : lgTop
          .map((r) => ({
            span_name: r.metric.span_name ?? "unknown",
            calls: parseFloat(r.value[1]),
          }))
          .filter((n) => Number.isFinite(n.calls) && n.calls > 0)
          .sort((a, b) => b.calls - a.calls);

  return {
    targets,
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
    lgCalls15m: firstSample(lgCalls),
    lgLatencyP95: firstSample(lgLat),
    lgActiveNodes: firstSample(lgNodes),
    lgTopNodes,
    lgCallsSpark: toSpark(lgCallsMatrix),
    cmePipeline: cmePipelineRaw,
    cmeServices: cmeServicesRaw,
    regReqRateSpark: toSpark(regReqMatrix),
    regLatencySpark: toSpark(regLatMatrix),
    nodeLoadSpark: toSpark(loadMatrix),
    lastUpdated: new Date(),
    reachable,
  };
}
