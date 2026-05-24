"use client";

import { useEffect, useRef, useState } from "react";

import type { Telemetry } from "@/components/dashboards/types";
import {
  POLL_MS,
  RANGE_WINDOW_SECONDS,
  RANGE_STEP_SECONDS,
  EMPTY,
  fetchTelemetry,
} from "@/components/dashboards/data";
import { SystemHeartbeatPanel } from "@/components/dashboards/system-heartbeat-panel";
import { GoldenSignalsPanel } from "@/components/dashboards/golden-signals-panel";
import { InfraPanel } from "@/components/dashboards/infra-panel";
import { LangGraphPanel } from "@/components/dashboards/langgraph-panel";
import { CmePipelinePanel } from "@/components/dashboards/cme-pipeline-panel";
import { ServiceLayerPanel } from "@/components/dashboards/service-layer-panel";
import { ExternalRefsPanel } from "@/components/dashboards/external-refs-panel";
import { FeedbackLoopPanel } from "@/components/dashboards/feedback-loop-panel";
import { DeferredIntelligencePanel } from "@/components/dashboards/deferred-intelligence-panel";

export default function DashboardsPage() {
  const [t, setT] = useState<Telemetry>(EMPTY);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const intervalRef = useRef<ReturnType<typeof setInterval> | undefined>(
    undefined,
  );

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      const next = await fetchTelemetry();
      if (!cancelled) setT(next);
    };
    run();
    intervalRef.current = setInterval(run, POLL_MS);
    const tickInt = setInterval(() => setNowMs(Date.now()), 1000);
    return () => {
      cancelled = true;
      if (intervalRef.current) clearInterval(intervalRef.current);
      clearInterval(tickInt);
    };
  }, []);

  const elapsedSec =
    t.lastUpdated != null
      ? Math.floor((nowMs - t.lastUpdated.getTime()) / 1000)
      : null;

  const allUp =
    t.targets != null && t.targets.every((tg) => tg.health === "up");
  const systemState = !t.reachable
    ? "LINK LOST"
    : allUp
      ? "NOMINAL"
      : "DEGRADED";
  const systemTone = !t.reachable ? "bad" : allUp ? "ok" : "warn";

  const now = new Date();
  const hh = String(now.getUTCHours()).padStart(2, "0");
  const mm = String(now.getUTCMinutes()).padStart(2, "0");
  const ss = String(now.getUTCSeconds()).padStart(2, "0");
  const utcStamp = `${hh}:${mm}:${ss}Z`;

  return (
    <div className="mc-root h-full overflow-y-auto">
      {/* =================== HEADER =================== */}
      <header className="border-b border-[color:var(--mc-frame)] px-6 py-4 mc-grid-bg">
        <div className="flex items-baseline justify-between gap-6">
          <div className="flex items-baseline gap-6">
            <span className="mc-cell">DHG/OPS</span>
            <h1 className="mc-readout text-[17px] tracking-[0.18em] uppercase text-[color:var(--mc-text)]">
              Mission Control
            </h1>
            <span className="mc-cell hidden md:inline">
              dhgaifactory3.5 · g700data1
            </span>
          </div>
          <div className="flex items-baseline gap-5">
            <span className="mc-cell">
              UTC <span className="mc-readout text-[13px] text-[color:var(--mc-text)]">{utcStamp}</span>
            </span>
            <span className="flex items-baseline gap-1.5">
              <span
                className={`mc-dot ${
                  t.reachable && allUp
                    ? "on mc-pulse"
                    : t.reachable
                      ? "off"
                      : "off"
                }`}
              />
              <span
                className={`mc-readout text-[13px] tracking-[0.16em] ${
                  systemTone === "ok"
                    ? "mc-ok"
                    : systemTone === "warn"
                      ? "mc-warn"
                      : "mc-bad"
                }`}
              >
                {systemState}
              </span>
            </span>
          </div>
        </div>
        <div className="mt-1.5 flex items-baseline justify-between">
          <p className="mc-cell max-w-xl">
            A live telemetry board for the DHG AI Factory. Panels refresh every
            10s. Values read directly from the Prometheus scrape fabric.
          </p>
          <span className="mc-cell">
            {elapsedSec === null
              ? "AWAITING FIRST FRAME"
              : `Δt ${elapsedSec}s since last frame`}
          </span>
        </div>
      </header>

      {/* =================== BODY GRID =================== */}
      <main className="p-6 grid gap-5 grid-cols-1 lg:grid-cols-12">
        <SystemHeartbeatPanel t={t} />
        <GoldenSignalsPanel t={t} />
        <InfraPanel t={t} />
        <LangGraphPanel t={t} />
        <CmePipelinePanel t={t} />
        <ServiceLayerPanel t={t} />
        <FeedbackLoopPanel t={t} />
        <DeferredIntelligencePanel t={t} />
        <ExternalRefsPanel />
      </main>

      {/* =================== FOOTER =================== */}
      <footer className="border-t border-[color:var(--mc-frame)] px-6 py-3 flex items-baseline justify-between">
        <span className="mc-cell">
          DHG AI FACTORY · MISSION CONTROL · v0.1
        </span>
        <span className="mc-cell">
          POLL {POLL_MS / 1000}s · WINDOW {RANGE_WINDOW_SECONDS / 60}m · STEP {RANGE_STEP_SECONDS}s
        </span>
      </footer>
    </div>
  );
}
