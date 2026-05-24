"use client";

import type { Telemetry } from "./types";
import { BORDERED_ROW } from "./data";
import { Panel, StatCard } from "./ui";

function priorityTone(priority: string): string {
  if (priority === "critical") return "mc-bad";
  if (priority === "high") return "mc-warn";
  return "mc-cell";
}

export function DeferredIntelligencePanel({ t }: { t: Telemetry }) {
  const ds = t.deferredStats;

  return (
    <Panel coord="H2" label="Deferred Intelligence · Backlog Health" className="lg:col-span-6">
      {ds === null ? (
        <div className="mc-cell py-4">DEFERRED DATA UNAVAILABLE</div>
      ) : (
        <>
          <div className="flex items-baseline gap-8 mb-4">
            <StatCard label="Total open" value={ds.by_status.open ?? 0} />
            <StatCard label="Resolved" value={ds.by_status.resolved ?? 0} />
            <StatCard label="Stale candidates" value={ds.stale_candidates} />
          </div>

          {/* Priority breakdown */}
          <div className="mc-label mb-2">By priority</div>
          <div className="flex items-baseline gap-4 mb-4">
            {Object.entries(ds.by_priority)
              .sort(([a], [b]) => {
                const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
                return (order[a] ?? 4) - (order[b] ?? 4);
              })
              .map(([priority, count]) => (
                <span key={priority} className="flex items-baseline gap-1.5">
                  <span className={`mc-readout text-[13px] tabular-nums ${priorityTone(priority)}`}>
                    {count}
                  </span>
                  <span className="mc-cell text-[10px]">{priority}</span>
                </span>
              ))}
          </div>

          <div className="mc-rule my-4" />

          {/* Category distribution */}
          <div className="mc-label mb-2">By category</div>
          {Object.entries(ds.by_category)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 10)
            .map(([cat, count]) => (
              <div key={cat} className={BORDERED_ROW}>
                <span className="mc-readout text-[12px] text-[color:var(--mc-text)]">{cat}</span>
                <span className="mc-readout text-[12px] mc-info tabular-nums">{count}</span>
              </div>
            ))}

          <div className="mc-rule my-4" />

          {/* Age distribution */}
          <div className="mc-label mb-2">Age distribution</div>
          <div className="flex items-baseline gap-4">
            {Object.entries(ds.age_histogram).map(([bucket, count]) => (
              <span key={bucket} className="flex items-baseline gap-1.5">
                <span className={`mc-readout text-[13px] tabular-nums ${
                  bucket === "30+d" && count > 0 ? "mc-warn" : "mc-info"
                }`}>
                  {count}
                </span>
                <span className="mc-cell text-[10px]">{bucket}</span>
              </span>
            ))}
          </div>
        </>
      )}
    </Panel>
  );
}
