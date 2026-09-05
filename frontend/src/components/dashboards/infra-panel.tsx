"use client";

import type { Telemetry } from "./types";
import {
  formatBytes,
  formatNumber,
  formatPercent,
  formatUptime,
} from "./data";
import { Panel, Row, Sparkline } from "./ui";

export function InfraPanel({ t }: { t: Telemetry }) {
  const incidentsActive = t.incidentStats?.by_status?.active ?? null;

  return (
    <>
      {/* === C1. POSTGRESQL ========================== */}
      <Panel coord="C1" label="PostgreSQL · Registry" className="lg:col-span-3">
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
          hint="registry-db"
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
        />
      </Panel>

      {/* === C7. HOST METRICS ======================== */}
      <Panel coord="C7" label="Host · g700data1" className="lg:col-span-3">
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

      {/* === C8. CONTAINERS ========================== */}
      <Panel coord="C8" label="Containers · cAdvisor" className="lg:col-span-3">
        <Row
          label="Running"
          value={formatNumber(t.containersRunning, { decimals: 0 })}
          hint="containers"
          tone="info"
        />
        <div className="mc-rule my-1.5" />
        <Row
          label="CPU · 5m"
          value={formatNumber(t.containerCpuCores, { decimals: 2 })}
          hint="cores"
        />
        <div className="mc-rule my-1.5" />
        <Row
          label="Memory working set"
          value={formatBytes(t.containerMemBytes)}
        />
        <div className="mc-rule my-1.5" />
        <Row
          label="Scrape targets"
          value={
            t.targetsTotal === null
              ? "——"
              : `${t.targetsTotal - (t.targetsDown ?? 0)}/${t.targetsTotal}`
          }
          hint={t.targetsDown === 0 ? "all up" : `${t.targetsDown ?? "——"} down`}
          tone={
            t.targetsDown === null ? "text" : t.targetsDown === 0 ? "ok" : "bad"
          }
        />
      </Panel>

      {/* === C9. REGISTRY INCIDENTS ================== */}
      <Panel
        coord="C9"
        label="Registry incidents (API)"
        className="lg:col-span-3"
      >
        <div className="py-2">
          <div
            className={`mc-readout text-[1.75rem] tracking-[0.08em] ${
              incidentsActive === null
                ? "mc-warn"
                : incidentsActive > 0
                  ? "mc-warn"
                  : "mc-ok"
            }`}
          >
            {formatNumber(incidentsActive, { decimals: 0 })}
            <span className="mc-delim text-[13px] ml-2">ACTIVE</span>
          </div>
          <div className="mc-cell mt-2">
            table count differs; fix tracked
          </div>
        </div>
        <div className="mc-rule my-2" />
        <Row
          label="Total recorded"
          value={formatNumber(t.incidentStats?.total ?? null, { decimals: 0 })}
        />
        <div className="mc-rule my-1.5" />
        <Row
          label="Resolved"
          value={formatNumber(t.incidentStats?.by_status?.resolved ?? null, {
            decimals: 0,
          })}
          tone="ok"
        />
      </Panel>
    </>
  );
}
