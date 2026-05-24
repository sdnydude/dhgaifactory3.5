"use client";

import type { Telemetry } from "./types";
import { BORDERED_ROW } from "./data";
import { Panel, StatCard } from "./ui";

function trendArrow(trend: string): string {
  if (trend === "increasing") return "▲";
  if (trend === "decreasing") return "▼";
  return "—";
}

function trendTone(trend: string): string {
  if (trend === "increasing") return "mc-warn";
  if (trend === "decreasing") return "mc-ok";
  return "mc-cell";
}

export function FeedbackLoopPanel({ t }: { t: Telemetry }) {
  const cs = t.correctionStats;
  const fh = t.feedbackHealth;

  return (
    <Panel coord="H1" label="Feedback Loop · Corrections & Pipeline Health" className="lg:col-span-6">
      {cs === null && fh === null ? (
        <div className="mc-cell py-4">FEEDBACK DATA UNAVAILABLE</div>
      ) : (
        <>
          {/* Correction stats */}
          {cs && (
            <>
              <div className="flex items-baseline gap-8 mb-4">
                <StatCard label="Corrections (7d)" value={cs.total_7d} />
                <StatCard label="30d" value={cs.total_30d} />
                <StatCard label="All time" value={cs.total_all} />
              </div>

              <div className="mc-label mb-2">Category breakdown</div>
              {cs.categories
                .filter((c) => c.count_7d > 0)
                .sort((a, b) => b.count_7d - a.count_7d)
                .map((c) => (
                  <div key={c.category} className={BORDERED_ROW}>
                    <span className="mc-readout text-[12px] text-[color:var(--mc-text)] flex items-center gap-2">
                      {c.category}
                      {c.repeat_flag && (
                        <span className="mc-readout text-[10px] mc-warn px-1 border border-current rounded">
                          REPEAT
                        </span>
                      )}
                    </span>
                    <span className="flex items-baseline gap-2">
                      <span className="mc-readout text-[12px] mc-info tabular-nums">
                        {c.count_7d}
                      </span>
                      <span className={`mc-readout text-[10px] ${trendTone(c.trend)}`}>
                        {trendArrow(c.trend)}
                      </span>
                    </span>
                  </div>
                ))}
            </>
          )}

          {/* Pipeline health */}
          {fh && (
            <>
              <div className="mc-rule my-4" />
              <div className="mc-label mb-2">Capture pipeline</div>
              <div className="flex items-baseline gap-3 mb-3">
                <span
                  className={`mc-readout text-[13px] ${
                    fh.status === "healthy" ? "mc-ok" : fh.status === "degraded" ? "mc-warn" : "mc-bad"
                  }`}
                >
                  {fh.status.toUpperCase()}
                </span>
                <span className="mc-cell">
                  {fh.healthy_types}/{fh.total_types} types active
                </span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {fh.types.map((tp) => (
                  <div
                    key={tp.type}
                    className="py-1.5 px-2 rounded border border-[color:var(--mc-frame)]/50"
                  >
                    <div className="mc-readout text-[11px] text-[color:var(--mc-text)] truncate">
                      {tp.type.replace(/_/g, " ")}
                    </div>
                    <div className="flex items-baseline gap-1.5 mt-0.5">
                      <span className={`mc-readout text-[13px] tabular-nums ${tp.count_7d > 0 ? "mc-ok" : "mc-warn"}`}>
                        {tp.count_7d}
                      </span>
                      <span className="mc-cell text-[10px]">7d</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </Panel>
  );
}
