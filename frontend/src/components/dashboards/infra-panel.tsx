"use client";

import type { Telemetry } from "./types";
import { formatNumber, formatPercent, formatUptime } from "./data";
import { Panel, Row, Sparkline } from "./ui";

export function InfraPanel({ t }: { t: Telemetry }) {
  return (
    <>
      {/* === C1. POSTGRESQL ========================== */}
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

      {/* === C7. HOST METRICS ======================== */}
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
    </>
  );
}
