"use client";

import { Panel } from "./ui";

export function ExternalRefsPanel() {
  return (
    <Panel
      coord="H1"
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
          {
            name: "LangSmith Cloud",
            url: "https://smith.langchain.com",
            note: "per-run LLM traces · external",
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
            <span className="mc-readout text-[14px] text-[color:var(--mc-text)] group-hover:mc-info transition-colors">
              {ref.name}
            </span>
            <span className="mc-cell">{ref.note}</span>
          </a>
        ))}
      </div>
    </Panel>
  );
}
