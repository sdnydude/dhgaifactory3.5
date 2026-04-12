"use client";

import { useEffect, useRef, useState } from "react";
import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";

const POLL_MS = 10_000;
const RANGE_WINDOW_SECONDS = 15 * 60;
const RANGE_STEP_SECONDS = 30;

type PromVectorResult = {
  metric: Record<string, string>;
  value: [number, string];
};

type PromMatrixResult = {
  metric: Record<string, string>;
  values: [number, string][];
};

type PromTarget = {
  labels: { job?: string; instance?: string };
  health: "up" | "down" | "unknown";
  lastScrape: string;
  scrapeUrl: string;
};

async function promQuery<T = PromVectorResult[]>(
  query: string,
): Promise<T | null> {
  try {
    const r = await fetch(
      `/api/prometheus/api/v1/query?query=${encodeURIComponent(query)}`,
      { cache: "no-store" },
    );
    if (!r.ok) return null;
    const j = await r.json();
    if (j.status !== "success") return null;
    return j.data.result as T;
  } catch {
    return null;
  }
}

async function promRange(
  query: string,
): Promise<PromMatrixResult[] | null> {
  try {
    const end = Math.floor(Date.now() / 1000);
    const start = end - RANGE_WINDOW_SECONDS;
    const r = await fetch(
      `/api/prometheus/api/v1/query_range?query=${encodeURIComponent(query)}&start=${start}&end=${end}&step=${RANGE_STEP_SECONDS}`,
      { cache: "no-store" },
    );
    if (!r.ok) return null;
    const j = await r.json();
    if (j.status !== "success") return null;
    return j.data.result as PromMatrixResult[];
  } catch {
    return null;
  }
}

async function fetchTargets(): Promise<PromTarget[] | null> {
  try {
    const r = await fetch(
      "/api/prometheus/api/v1/targets?state=active",
      { cache: "no-store" },
    );
    if (!r.ok) return null;
    const j = await r.json();
    return j.data.activeTargets as PromTarget[];
  } catch {
    return null;
  }
}

async function fetchAlerts(): Promise<number | null> {
  try {
    const r = await fetch("/api/alertmanager/api/v2/alerts", {
      cache: "no-store",
    });
    if (!r.ok) return null;
    const j = (await r.json()) as { status: { state: string } }[];
    return j.filter((a) => a.status?.state === "active").length;
  } catch {
    return null;
  }
}

function firstSample(result: PromVectorResult[] | null): number | null {
  if (!result || result.length === 0) return null;
  const v = parseFloat(result[0].value[1]);
  return Number.isFinite(v) ? v : null;
}

function toSpark(matrix: PromMatrixResult[] | null): { v: number }[] {
  if (!matrix || matrix.length === 0) return [];
  return matrix[0].values
    .map(([, val]) => ({ v: parseFloat(val) }))
    .filter((p) => Number.isFinite(p.v));
}

function formatNumber(
  n: number | null,
  opts: { decimals?: number; unit?: string; ifNull?: string } = {},
): string {
  if (n === null || !Number.isFinite(n)) return opts.ifNull ?? "——";
  const { decimals = 0, unit = "" } = opts;
  return `${n.toFixed(decimals)}${unit}`;
}

function formatPercent(n: number | null, decimals = 1): string {
  if (n === null || !Number.isFinite(n)) return "——";
  return `${(n * 100).toFixed(decimals)}%`;
}

function formatUptime(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return "——";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

interface Telemetry {
  targets: PromTarget[] | null;
  alertsFiring: number | null;

  regReqRate: number | null;
  regErrRate: number | null;
  regLatencyP95: number | null;

  pgConnections: number | null;
  pgCacheHit: number | null;
  pgUp: number | null;

  nodeLoad1: number | null;
  nodeMemAvailPct: number | null;
  promUptime: number | null;

  regReqRateSpark: { v: number }[];
  regLatencySpark: { v: number }[];
  nodeLoadSpark: { v: number }[];

  lastUpdated: Date | null;
  reachable: boolean;
}

const EMPTY: Telemetry = {
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
  regReqRateSpark: [],
  regLatencySpark: [],
  nodeLoadSpark: [],
  lastUpdated: null,
  reachable: true,
};

async function fetchTelemetry(): Promise<Telemetry> {
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
    regReqMatrix,
    regLatMatrix,
    loadMatrix,
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
    promRange('sum(rate(http_requests_total{job="registry-api"}[1m]))'),
    promRange(
      'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="registry-api"}[5m])))',
    ),
    promRange("node_load1"),
  ]);

  const reachable = targets !== null;

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
    regReqRateSpark: toSpark(regReqMatrix),
    regLatencySpark: toSpark(regLatMatrix),
    nodeLoadSpark: toSpark(loadMatrix),
    lastUpdated: new Date(),
    reachable,
  };
}

function Sparkline({
  data,
  color,
}: {
  data: { v: number }[];
  color: string;
}) {
  if (data.length < 2) {
    return <div className="h-8 mc-cell flex items-center">—— no signal</div>;
  }
  return (
    <div className="h-8 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.25}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function Panel({
  coord,
  label,
  children,
  className = "",
}: {
  coord: string;
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`mc-panel ${className}`}>
      <header className="flex items-baseline justify-between mb-3">
        <div className="flex items-baseline gap-2.5">
          <span className="mc-cell">{coord}</span>
          <span className="mc-label">{label}</span>
        </div>
        <span className="mc-cell">◦</span>
      </header>
      {children}
    </section>
  );
}

function Row({
  label,
  value,
  hint,
  tone = "text",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "text" | "ok" | "warn" | "bad" | "info";
}) {
  const toneClass = {
    text: "",
    ok: "mc-ok",
    warn: "mc-warn",
    bad: "mc-bad",
    info: "mc-info",
  }[tone];
  return (
    <div className="flex items-baseline justify-between py-1.5 gap-3">
      <span className="mc-label">{label}</span>
      <span className="flex items-baseline gap-1.5">
        <span className={`mc-readout text-[13px] ${toneClass}`}>{value}</span>
        {hint && <span className="mc-cell">{hint}</span>}
      </span>
    </div>
  );
}

export default function DashboardsPage() {
  const [t, setT] = useState<Telemetry>(EMPTY);
  const [tick, setTick] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | undefined>(
    undefined,
  );

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      const next = await fetchTelemetry();
      if (!cancelled) setT(next);
    };
    run();
    intervalRef.current = setInterval(run, POLL_MS);
    const tickInt = setInterval(() => setTick((x) => x + 1), 1000);
    return () => {
      cancelled = true;
      if (intervalRef.current) clearInterval(intervalRef.current);
      clearInterval(tickInt);
    };
  }, []);

  const elapsedSec =
    t.lastUpdated != null
      ? Math.floor((Date.now() - t.lastUpdated.getTime()) / 1000)
      : null;

  const allUp =
    t.targets != null && t.targets.every((tg) => tg.health === "up");
  const systemState = !t.reachable
    ? "LINK LOST"
    : allUp
      ? "NOMINAL"
      : "DEGRADED";
  const systemTone = !t.reachable ? "bad" : allUp ? "ok" : "warn";

  const firingLabel =
    t.alertsFiring === null
      ? "——"
      : t.alertsFiring === 0
        ? "0 FIRING"
        : `${t.alertsFiring} FIRING`;
  const firingTone =
    t.alertsFiring === null ? "text" : t.alertsFiring === 0 ? "ok" : "bad";

  const now = new Date();
  const hh = String(now.getUTCHours()).padStart(2, "0");
  const mm = String(now.getUTCMinutes()).padStart(2, "0");
  const ss = String(now.getUTCSeconds()).padStart(2, "0");
  const utcStamp = `${hh}:${mm}:${ss}Z`;

  void tick;

  return (
    <div className="mc-root">
      {/* =================== HEADER =================== */}
      <header className="border-b border-[color:var(--mc-frame)] px-6 py-4 mc-grid-bg">
        <div className="flex items-baseline justify-between gap-6">
          <div className="flex items-baseline gap-6">
            <span className="mc-cell">DHG/OPS</span>
            <h1 className="mc-readout text-[15px] tracking-[0.18em] uppercase text-[color:var(--mc-text)]">
              Mission Control
            </h1>
            <span className="mc-cell hidden md:inline">
              dhgaifactory3.5 · g700data1
            </span>
          </div>
          <div className="flex items-baseline gap-5">
            <span className="mc-cell">
              UTC <span className="mc-readout text-[11px] text-[color:var(--mc-text)]">{utcStamp}</span>
            </span>
            <span className="flex items-baseline gap-1.5">
              <span
                className={`mc-dot ${
                  t.reachable && allUp
                    ? "on mc-pulse"
                    : t.reachable
                      ? "off"
                      : "off"
                }`}
              />
              <span
                className={`mc-readout text-[11px] tracking-[0.16em] ${
                  systemTone === "ok"
                    ? "mc-ok"
                    : systemTone === "warn"
                      ? "mc-warn"
                      : "mc-bad"
                }`}
              >
                {systemState}
              </span>
            </span>
          </div>
        </div>
        <div className="mt-1.5 flex items-baseline justify-between">
          <p className="mc-cell max-w-xl">
            A live telemetry board for the DHG AI Factory. Panels refresh every
            10s. Values read directly from the Prometheus scrape fabric.
          </p>
          <span className="mc-cell">
            {elapsedSec === null
              ? "AWAITING FIRST FRAME"
              : `Δt ${elapsedSec}s since last frame`}
          </span>
        </div>
      </header>

      {/* =================== BODY GRID =================== */}
      <main className="p-6 grid gap-5 grid-cols-1 lg:grid-cols-12">
        {/* === A. SYSTEM HEARTBEAT ===================== */}
        <Panel
          coord="A1"
          label="System Heartbeat · Scrape Targets"
          className="lg:col-span-12"
        >
          {t.targets === null && (
            <div className="mc-cell py-4">PROMETHEUS UNREACHABLE — —— —— ——</div>
          )}
          {t.targets !== null && t.targets.length === 0 && (
            <div className="mc-cell py-4">NO ACTIVE TARGETS</div>
          )}
          {t.targets !== null && t.targets.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
              {t.targets
                .slice()
                .sort((a, b) =>
                  (a.labels.job ?? "").localeCompare(b.labels.job ?? ""),
                )
                .map((tg) => (
                  <div
                    key={`${tg.labels.job}-${tg.labels.instance}`}
                    className="mc-heartbeat-tile"
                    data-status={tg.health}
                  >
                    <div className="flex items-baseline justify-between mb-1.5">
                      <span className="mc-label text-[color:var(--mc-text)]">
                        {tg.labels.job ?? "unknown"}
                      </span>
                      <span
                        className={`mc-dot ${
                          tg.health === "up"
                            ? "on"
                            : tg.health === "down"
                              ? "off"
                              : ""
                        }`}
                      />
                    </div>
                    <div className="mc-cell truncate">
                      {tg.labels.instance ?? "—"}
                    </div>
                    <div
                      className={`mc-readout text-[10px] mt-1 ${
                        tg.health === "up"
                          ? "mc-ok"
                          : tg.health === "down"
                            ? "mc-bad"
                            : "mc-warn"
                      }`}
                    >
                      {tg.health.toUpperCase()}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </Panel>

        {/* === B. GOLDEN SIGNALS — REGISTRY API ======== */}
        <Panel
          coord="B1"
          label="Golden Signals · Registry API"
          className="lg:col-span-8"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div>
              <div className="mc-label mb-1.5">Request rate · 1m</div>
              <div className="mc-value-lg mc-info mc-readout">
                {formatNumber(t.regReqRate, { decimals: 2 })}
                <span className="mc-delim text-[11px] ml-1">req/s</span>
              </div>
              <div className="mt-2">
                <Sparkline
                  data={t.regReqRateSpark}
                  color="var(--mc-cyan-dim)"
                />
              </div>
            </div>
            <div>
              <div className="mc-label mb-1.5">Error rate · 5xx/total</div>
              <div
                className={`mc-value-lg mc-readout ${
                  t.regErrRate !== null && t.regErrRate > 0.01
                    ? "mc-bad"
                    : "mc-ok"
                }`}
              >
                {formatPercent(t.regErrRate, 2)}
              </div>
              <div className="mc-cell mt-3">
                {t.regErrRate === null
                  ? "NO READING"
                  : t.regErrRate === 0
                    ? "ZERO 5xx IN WINDOW"
                    : "WATCH FOR CLIMBING 5xx"}
              </div>
            </div>
            <div>
              <div className="mc-label mb-1.5">Latency · p95</div>
              <div className="mc-value-lg mc-readout">
                {t.regLatencyP95 !== null
                  ? `${(t.regLatencyP95 * 1000).toFixed(0)}`
                  : "——"}
                <span className="mc-delim text-[11px] ml-1">ms</span>
              </div>
              <div className="mt-2">
                <Sparkline
                  data={t.regLatencySpark}
                  color="var(--mc-phosphor-dim)"
                />
              </div>
            </div>
          </div>
        </Panel>

        {/* === C. ALERTMANAGER ========================= */}
        <Panel coord="B9" label="Alertmanager" className="lg:col-span-4">
          <div className="py-3">
            <div
              className={`mc-readout text-[1.4rem] tracking-[0.1em] ${
                firingTone === "ok"
                  ? "mc-ok"
                  : firingTone === "bad"
                    ? "mc-bad mc-blink"
                    : "mc-warn"
              }`}
            >
              {firingLabel}
            </div>
            <div className="mc-cell mt-2">
              {t.alertsFiring === null
                ? "ALERTMANAGER UNREACHABLE"
                : t.alertsFiring === 0
                  ? "ALL CLEAR · NOTHING ACTIVE"
                  : "ACTIVE ALERTS REQUIRE ATTENTION"}
            </div>
          </div>
          <div className="mc-rule my-3" />
          <div className="mc-cell">
            alertmanager:9093 · routed via /api/alertmanager
          </div>
        </Panel>

        {/* === D. POSTGRESQL =========================== */}
        <Panel coord="C1" label="PostgreSQL · Registry" className="lg:col-span-6">
          <Row
            label="STATE"
            value={
              t.pgUp === 1
                ? "UP"
                : t.pgUp === 0
                  ? "DOWN"
                  : "——"
            }
            tone={t.pgUp === 1 ? "ok" : t.pgUp === 0 ? "bad" : "text"}
          />
          <div className="mc-rule my-1.5" />
          <Row
            label="Active connections"
            value={formatNumber(t.pgConnections, { decimals: 0 })}
            hint="count"
          />
          <div className="mc-rule my-1.5" />
          <Row
            label="Cache hit ratio"
            value={formatPercent(t.pgCacheHit, 2)}
            tone={
              t.pgCacheHit === null
                ? "text"
                : t.pgCacheHit > 0.98
                  ? "ok"
                  : t.pgCacheHit > 0.9
                    ? "warn"
                    : "bad"
            }
            hint={
              t.pgCacheHit !== null && t.pgCacheHit > 0.98
                ? "healthy"
                : undefined
            }
          />
        </Panel>

        {/* === E. HOST METRICS ========================= */}
        <Panel coord="C7" label="Host · g700data1" className="lg:col-span-6">
          <Row
            label="Load · 1m"
            value={formatNumber(t.nodeLoad1, { decimals: 2 })}
          />
          <div className="mt-1.5">
            <Sparkline data={t.nodeLoadSpark} color="var(--mc-amber-dim)" />
          </div>
          <div className="mc-rule my-2" />
          <Row
            label="Memory available"
            value={formatPercent(t.nodeMemAvailPct, 1)}
            tone={
              t.nodeMemAvailPct === null
                ? "text"
                : t.nodeMemAvailPct > 0.25
                  ? "ok"
                  : t.nodeMemAvailPct > 0.1
                    ? "warn"
                    : "bad"
            }
          />
          <div className="mc-rule my-1.5" />
          <Row
            label="Prometheus uptime"
            value={formatUptime(t.promUptime)}
            tone="info"
          />
        </Panel>

        {/* === F. EXTERNAL REFS ======================== */}
        <Panel
          coord="D1"
          label="Deep Inspect · External Boards"
          className="lg:col-span-12"
        >
          <div className="flex flex-wrap gap-x-8 gap-y-3">
            {[
              {
                name: "Grafana",
                url: "http://10.0.0.251:3001",
                note: "full dashboards · LAN only",
              },
              {
                name: "Prometheus",
                url: "http://10.0.0.251:9090",
                note: "raw PromQL · LAN only",
              },
              {
                name: "Alertmanager",
                url: "http://10.0.0.251:9093",
                note: "alert routing · LAN only",
              },
              {
                name: "Tempo",
                url: "http://10.0.0.251:3200",
                note: "trace search · LAN only",
              },
            ].map((ref) => (
              <a
                key={ref.name}
                href={ref.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group inline-flex items-baseline gap-2"
              >
                <span className="mc-cell">→</span>
                <span className="mc-readout text-[12px] text-[color:var(--mc-text)] group-hover:mc-info transition-colors">
                  {ref.name}
                </span>
                <span className="mc-cell">{ref.note}</span>
              </a>
            ))}
          </div>
        </Panel>
      </main>

      {/* =================== FOOTER =================== */}
      <footer className="border-t border-[color:var(--mc-frame)] px-6 py-3 flex items-baseline justify-between">
        <span className="mc-cell">
          DHG AI FACTORY · MISSION CONTROL · v0.1
        </span>
        <span className="mc-cell">
          POLL {POLL_MS / 1000}s · WINDOW {RANGE_WINDOW_SECONDS / 60}m · STEP {RANGE_STEP_SECONDS}s
        </span>
      </footer>
    </div>
  );
}
