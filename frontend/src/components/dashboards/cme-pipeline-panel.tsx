"use client";

import type { Telemetry } from "./types";
import { formatUptime, statusTone, BORDERED_ROW } from "./data";
import { Panel, QualityBadge, StatCard } from "./ui";

export function CmePipelinePanel({ t }: { t: Telemetry }) {
  return (
    <Panel
      coord="F1"
      label="CME Pipeline · Agent Telemetry"
      className="lg:col-span-12"
    >
      {t.cmePipeline === null ? (
        <div className="mc-cell py-4">CME PIPELINE DATA UNAVAILABLE</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <StatCard label="Projects" value={t.cmePipeline.total_projects} />
            <StatCard label="Pipeline runs" value={t.cmePipeline.total_runs} />
            <StatCard label="Documents" value={t.cmePipeline.total_documents} />
            <StatCard label="References" value={t.cmePipeline.total_references} />
            <StatCard label="Avg run duration" value={formatUptime(t.cmePipeline.avg_run_duration_sec)} />
          </div>

          <div className="mc-rule my-4" />

          <div className="mc-label mb-2">Projects by status</div>
          <div className="flex flex-wrap gap-4">
            {Object.entries(t.cmePipeline.projects_by_status).map(
              ([status, count]) => (
                <div key={status} className="flex items-baseline gap-1.5">
                  <span className={`mc-readout text-[1.1rem] ${statusTone(status)}`}>
                    {count}
                  </span>
                  <span className="mc-cell">{status.toUpperCase()}</span>
                </div>
              ),
            )}
          </div>

          <div className="mc-rule my-4" />

          <div className="mc-label mb-2">Agent completion · count + quality score</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
            {t.cmePipeline.agent_completion.map((a) => (
              <div key={a.agent} className={BORDERED_ROW}>
                <span className="mc-readout text-[13px] text-[color:var(--mc-text)] uppercase tracking-wider">
                  {a.agent.replace(/_/g, " ")}
                </span>
                <span className="flex items-baseline gap-3">
                  <span className="mc-readout text-[13px] mc-info tabular-nums">
                    {a.count}
                  </span>
                  <QualityBadge score={a.avg_quality} />
                </span>
              </div>
            ))}
          </div>

          <div className="mc-rule my-4" />

          <div className="mc-label mb-2">Document throughput · count + avg words + quality</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
            {t.cmePipeline.document_throughput.map((d) => (
              <div key={d.type} className={BORDERED_ROW}>
                <span className="mc-readout text-[13px] text-[color:var(--mc-text)] uppercase tracking-wider">
                  {d.type.replace(/_/g, " ")}
                </span>
                <span className="flex items-baseline gap-3">
                  <span className="mc-readout text-[13px] mc-info tabular-nums">
                    {d.count}
                  </span>
                  <span className="mc-cell tabular-nums">
                    {d.avg_words > 0 ? `${d.avg_words}w` : "——"}
                  </span>
                  <QualityBadge score={d.avg_quality} />
                </span>
              </div>
            ))}
          </div>

          {t.cmePipeline.active_pipelines.length > 0 && (
            <>
              <div className="mc-rule my-4" />
              <div className="mc-label mb-2">Active pipelines</div>
              <div className="grid grid-cols-1 gap-2.5">
                {t.cmePipeline.active_pipelines.map((p) => (
                  <div
                    key={p.project_id}
                    className="flex items-center gap-3 py-2 border-b border-[color:var(--mc-frame)]/40"
                  >
                    <span className="mc-dot on mc-pulse" />
                    <span className="mc-readout text-[13px] text-[color:var(--mc-text)] truncate flex-1">
                      {p.name}
                    </span>
                    <span className="mc-cell uppercase">
                      {p.current_agent?.replace(/_/g, " ") ?? "——"}
                    </span>
                    <span className="mc-readout text-[13px] mc-warn tabular-nums">
                      {p.progress_percent}%
                    </span>
                    <div className="w-24 h-1.5 rounded-full bg-[color:var(--mc-frame)] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[color:var(--mc-amber)]"
                        style={{ width: `${p.progress_percent}%` }}
                      />
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
