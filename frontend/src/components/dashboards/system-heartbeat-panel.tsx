"use client";

import type { Telemetry } from "./types";
import { Panel } from "./ui";

export function SystemHeartbeatPanel({ t }: { t: Telemetry }) {
  return (
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
                  className={`mc-readout text-[12px] mt-1 ${
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
  );
}
