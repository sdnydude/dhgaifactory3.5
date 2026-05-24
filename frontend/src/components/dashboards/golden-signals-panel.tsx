"use client";

import type { Telemetry } from "./types";
import { formatNumber, formatPercent } from "./data";
import { Panel, Sparkline } from "./ui";

export function GoldenSignalsPanel({ t }: { t: Telemetry }) {
  const firingLabel =
    t.alertsFiring === null
      ? "——"
      : t.alertsFiring === 0
        ? "0 FIRING"
        : `${t.alertsFiring} FIRING`;
  const firingTone =
    t.alertsFiring === null ? "text" : t.alertsFiring === 0 ? "ok" : "bad";

  return (
    <>
      {/* === B1. GOLDEN SIGNALS — REGISTRY API ======= */}
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
              <span className="mc-delim text-[13px] ml-1">req/s</span>
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
              <span className="mc-delim text-[13px] ml-1">ms</span>
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

      {/* === B9. ALERTMANAGER ======================== */}
      <Panel coord="B9" label="Alertmanager" className="lg:col-span-4">
        <div className="py-3">
          <div
            className={`mc-readout text-[1.75rem] tracking-[0.1em] ${
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
    </>
  );
}
