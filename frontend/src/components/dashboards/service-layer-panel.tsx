"use client";

import type { Telemetry } from "./types";
import { BORDERED_ROW } from "./data";
import { Panel, StatCard } from "./ui";

export function ServiceLayerPanel({ t }: { t: Telemetry }) {
  return (
    <Panel
      coord="G1"
      label="Service Layer · Registry Modules"
      className="lg:col-span-12"
    >
      {t.cmeServices === null ? (
        <div className="mc-cell py-4">SERVICE DATA UNAVAILABLE</div>
      ) : (
        <>
          <div className="flex items-baseline gap-8 mb-4">
            <StatCard label="Service modules" value={t.cmeServices.service_count} />
            <StatCard label="DB connections" value={t.cmeServices.db_active_connections} />
            <StatCard label="Tables tracked" value={Object.keys(t.cmeServices.table_counts).length} />
          </div>

          <div className="mc-rule my-4" />

          <div className="mc-label mb-2">Registered services</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {t.cmeServices.services.map((s) => (
              <div
                key={s.name}
                className="flex items-center gap-2 py-1.5 px-2 rounded border border-[color:var(--mc-frame)]/50"
              >
                <span className="mc-readout text-[11px] text-[color:var(--mc-text)] truncate">
                  {s.domain}
                </span>
              </div>
            ))}
          </div>

          <div className="mc-rule my-4" />

          <div className="mc-label mb-2">Table populations (est) · top 20</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
            {Object.entries(t.cmeServices.table_counts)
              .filter(([, count]) => count > 0)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 20)
              .map(([table, count]) => (
                <div key={table} className={BORDERED_ROW}>
                  <span className="mc-readout text-[12px] text-[color:var(--mc-text)] truncate">
                    {table}
                  </span>
                  <span className="mc-readout text-[12px] mc-info tabular-nums">
                    {count.toLocaleString()}
                  </span>
                </div>
              ))}
          </div>
        </>
      )}
    </Panel>
  );
}
