"use client";

import type { ReviewMetrics } from "./types";

interface ReflectionPanelProps {
  metrics: ReviewMetrics;
  recipe: string;
  reviewRound: number;
}

type Verdict = "approve" | "revise" | "attention";

function buildRecommendation(metrics: ReviewMetrics): {
  verdict: Verdict;
  headline: string;
  note: string;
} {
  const issues: string[] = [];

  if (metrics.quality_passed === false) {
    issues.push("the prose-quality gate has failed");
  }
  if (metrics.banned_patterns_found && metrics.banned_patterns_found.length > 0) {
    issues.push(
      `${metrics.banned_patterns_found.length} banned pattern${metrics.banned_patterns_found.length === 1 ? "" : "s"} detected`,
    );
  }
  if (metrics.compliance_result) {
    const compliance = metrics.compliance_result as Record<string, unknown>;
    if (compliance.passed === false) {
      issues.push("the ACCME compliance check did not clear");
    }
  }

  if (issues.length === 0) {
    return {
      verdict: "approve",
      headline: "The gates stand open",
      note: `All quality gates have cleared. ${metrics.word_count ? `The manuscript runs to ${metrics.word_count.toLocaleString()} words` : "The manuscript has been tallied"}${metrics.prose_density ? `, with a prose density of ${(metrics.prose_density * 100).toFixed(0)} percent` : ""}. No banned patterns surfaced; compliance was verified. In the judgment of your editors, this document is fit for the press.`,
    };
  }

  return {
    verdict: issues.length >= 2 ? "attention" : "revise",
    headline:
      issues.length >= 2 ? "The editors advise caution" : "A revision is recommended",
    note: `Before the press receives this manuscript, ${issues.join(", and ")}. Review the flagged sections carefully — the author may wish to address these matters before a final verdict is rendered.`,
  };
}

export function ReflectionPanel({ metrics, reviewRound }: ReflectionPanelProps) {
  const rec = buildRecommendation(metrics);

  const verdictColor =
    rec.verdict === "approve"
      ? "var(--color-dhg-orange)"
      : rec.verdict === "revise"
        ? "var(--color-dhg-orange)"
        : "#B91C1C";

  const verdictLabel =
    rec.verdict === "approve"
      ? "Press permitted"
      : rec.verdict === "revise"
        ? "Revise & resubmit"
        : "Editorial concern";

  return (
    <section
      className="relative mb-8 py-5 px-7 border-y border-foreground/80"
      style={{ borderTopWidth: "1.5px" }}
    >
      <div className="flex items-baseline justify-between gap-4 mb-3">
        <p
          className="font-display italic text-[10px] small-caps text-muted-foreground"
          style={{ fontVariationSettings: '"SOFT" 40, "opsz" 10' }}
        >
          Publisher&rsquo;s note
        </p>
        <div className="flex items-center gap-3">
          {reviewRound > 0 && (
            <span className="font-mono-editorial small-caps text-[9px] text-muted-foreground tabular-nums">
              Round {reviewRound}
            </span>
          )}
          <span
            className="font-mono-editorial small-caps text-[9px] font-medium tabular-nums"
            style={{ color: verdictColor }}
          >
            · {verdictLabel}
          </span>
        </div>
      </div>

      <h2
        className="font-display italic text-[1.55rem] text-foreground leading-tight"
        style={{
          fontVariationSettings: '"SOFT" 70, "opsz" 96',
          letterSpacing: "-0.01em",
        }}
      >
        {rec.headline}.
      </h2>

      <p className="font-serif-body text-[13.5px] text-foreground/80 mt-3 leading-relaxed max-w-[52rem]">
        {rec.note}
      </p>

      {metrics.banned_patterns_found && metrics.banned_patterns_found.length > 0 && (
        <div className="mt-5 pt-4 border-t border-border">
          <p
            className="font-display italic text-[10px] small-caps text-muted-foreground mb-2"
            style={{ fontVariationSettings: '"SOFT" 40, "opsz" 10' }}
          >
            Flagged phrases
          </p>
          <ul className="flex flex-wrap gap-x-5 gap-y-1">
            {metrics.banned_patterns_found.map((pattern, i) => (
              <li
                key={pattern}
                className="font-mono-editorial text-[11px] text-destructive"
              >
                <sup className="text-[8px] mr-0.5 opacity-70">{i + 1}</sup>
                {pattern}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Signed */}
      <p
        className="mt-5 text-right font-display italic text-[11px] text-muted-foreground"
        style={{ fontVariationSettings: '"SOFT" 60, "opsz" 12' }}
      >
        — Compiled by the reflection engine
      </p>
    </section>
  );
}
