"use client";

import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";
import { qualityTone } from "./data";

export function Sparkline({
  data,
  color,
}: {
  data: { v: number }[];
  color: string;
}) {
  if (data.length < 2) {
    return <div className="h-8 mc-cell flex items-center">—— no signal</div>;
  }
  return (
    <div className="h-8 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.25}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Panel({
  coord,
  label,
  children,
  className = "",
}: {
  coord: string;
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`mc-panel ${className}`}>
      <header className="flex items-baseline justify-between mb-3">
        <div className="flex items-baseline gap-2.5">
          <span className="mc-cell">{coord}</span>
          <span className="mc-label">{label}</span>
        </div>
        <span className="mc-cell">◦</span>
      </header>
      {children}
    </section>
  );
}

export function Row({
  label,
  value,
  hint,
  tone = "text",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "text" | "ok" | "warn" | "bad" | "info";
}) {
  const toneClass = {
    text: "",
    ok: "mc-ok",
    warn: "mc-warn",
    bad: "mc-bad",
    info: "mc-info",
  }[tone];
  return (
    <div className="flex items-baseline justify-between py-1.5 gap-3">
      <span className="mc-label">{label}</span>
      <span className="flex items-baseline gap-1.5">
        <span className={`mc-readout text-[15px] ${toneClass}`}>{value}</span>
        {hint && <span className="mc-cell">{hint}</span>}
      </span>
    </div>
  );
}

export function QualityBadge({ score }: { score: number | null }) {
  return (
    <span className={`mc-readout text-[13px] tabular-nums ${qualityTone(score)}`}>
      {score !== null ? score.toFixed(2) : "——"}
    </span>
  );
}

export function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="mc-label mb-1">{label}</div>
      <div className="mc-readout text-[1.25rem] mc-info">{value}</div>
    </div>
  );
}
