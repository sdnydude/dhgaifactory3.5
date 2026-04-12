"use client";

import type { ReviewMetrics } from "./types";

interface MetricsBarProps {
  metrics: ReviewMetrics;
  reviewRound: number;
}

interface Footnote {
  marker: string;
  label: string;
  value: string;
  tone: "neutral" | "good" | "warn" | "bad";
}

export function MetricsBar({ metrics, reviewRound }: MetricsBarProps) {
  const footnotes: Footnote[] = [];

  if (metrics.word_count != null) {
    footnotes.push({
      marker: "i",
      label: "Extent",
      value: `${metrics.word_count.toLocaleString()} wd`,
      tone: "neutral",
    });
  }
  if (metrics.prose_density != null) {
    footnotes.push({
      marker: "ii",
      label: "Density",
      value: `${(metrics.prose_density * 100).toFixed(0)}%`,
      tone: "neutral",
    });
  }
  if (metrics.quality_passed != null) {
    footnotes.push({
      marker: "iii",
      label: "Prose QA",
      value: metrics.quality_passed ? "cleared" : "failed",
      tone: metrics.quality_passed ? "good" : "bad",
    });
  }
  if (metrics.banned_patterns_found && metrics.banned_patterns_found.length > 0) {
    footnotes.push({
      marker: "iv",
      label: "Banned phrases",
      value: `${metrics.banned_patterns_found.length} found`,
      tone: "bad",
    });
  }
  if (reviewRound > 0) {
    footnotes.push({
      marker: "v",
      label: "Revision",
      value: `${reviewRound} of 3`,
      tone: "warn",
    });
  }

  if (footnotes.length === 0) {
    return null;
  }

  const toneColor: Record<Footnote["tone"], string> = {
    neutral: "var(--muted-foreground)",
    good: "#0E7C3A",
    warn: "var(--color-dhg-orange)",
    bad: "#B91C1C",
  };

  return (
    <aside className="flex flex-wrap items-baseline gap-x-6 gap-y-2 py-3 border-y border-border">
      <p
        className="font-display italic text-[10px] small-caps text-muted-foreground"
        style={{ fontVariationSettings: '"SOFT" 40, "opsz" 10' }}
      >
        Footnotes
      </p>
      {footnotes.map((f) => (
        <span key={f.marker} className="inline-flex items-baseline gap-1">
          <sup
            className="font-display italic text-[9px] tabular-nums"
            style={{
              color: toneColor[f.tone],
              fontVariationSettings: '"SOFT" 30, "opsz" 8',
            }}
          >
            {f.marker}.
          </sup>
          <span className="font-mono-editorial small-caps text-[10px] text-muted-foreground">
            {f.label}
          </span>
          <span
            className="font-mono-editorial tabular-nums text-[11px] font-medium"
            style={{ color: toneColor[f.tone] }}
          >
            {f.value}
          </span>
        </span>
      ))}
    </aside>
  );
}
