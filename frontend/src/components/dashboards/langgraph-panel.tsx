"use client";

import type { Telemetry } from "./types";
import { formatNumber, BORDERED_ROW } from "./data";
import { Panel, Sparkline } from "./ui";

export function LangGraphPanel({ t }: { t: Telemetry }) {
  return (
    <Panel
      coord="D1"
      label="LangGraph Agents · Span Telemetry"
      className="lg:col-span-12"
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div>
          <div className="mc-label mb-1.5">Node invocations · 15m</div>
          <div className="mc-value-lg mc-info mc-readout">
            {formatNumber(t.lgCalls15m, { decimals: 0 })}
            <span className="mc-delim text-[13px] ml-1">calls</span>
          </div>
          <div className="mt-2">
            <Sparkline
              data={t.lgCallsSpark}
              color="var(--mc-cyan-dim)"
            />
          </div>
        </div>
        <div>
          <div className="mc-label mb-1.5">Latency · p95 · 5m</div>
          <div className="mc-value-lg mc-readout">
            {t.lgLatencyP95 !== null
              ? `${(t.lgLatencyP95 * 1000).toFixed(0)}`
              : "——"}
            <span className="mc-delim text-[13px] ml-1">ms</span>
          </div>
          <div className="mc-cell mt-3">
            {t.lgLatencyP95 === null
              ? "NO HISTOGRAM DATA"
              : "derived from spanmetrics latency bucket"}
          </div>
        </div>
        <div>
          <div className="mc-label mb-1.5">Active nodes</div>
          <div className="mc-value-lg mc-readout">
            {formatNumber(t.lgActiveNodes, { decimals: 0 })}
            <span className="mc-delim text-[13px] ml-1">span names</span>
          </div>
          <div className="mc-cell mt-3">
            {t.lgActiveNodes === null
              ? "NO READING"
              : `${t.lgActiveNodes} distinct @traced_node decorators observed`}
          </div>
        </div>
      </div>

      <div className="mc-rule my-4" />

      <div className="mc-label mb-2">Top nodes by call count · 15m</div>
      {t.lgTopNodes === null && (
        <div className="mc-cell py-3">NO TELEMETRY — SPANMETRICS UNAVAILABLE</div>
      )}
      {t.lgTopNodes !== null && t.lgTopNodes.length === 0 && (
        <div className="mc-cell py-3">
          NO CALLS IN WINDOW — TRIGGER A GRAPH RUN TO POPULATE
        </div>
      )}
      {t.lgTopNodes !== null && t.lgTopNodes.length > 0 && (
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
          {t.lgTopNodes.map((node) => (
            <li
              key={node.span_name}
              className={`${BORDERED_ROW} gap-3`}
            >
              <span className="mc-readout text-[13px] text-[color:var(--mc-text)] truncate">
                {node.span_name}
              </span>
              <span className="mc-readout text-[13px] mc-info tabular-nums">
                {node.calls.toFixed(0)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
