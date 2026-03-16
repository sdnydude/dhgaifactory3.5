"use client";

import { useState } from "react";
import { VsSparkline } from "./vs-sparkline";
import type { ThreadState, VsDistribution } from "@/lib/agentsApi";

const STEP_LABELS: Record<string, string> = {
  epidemiology: "Epidemiology",
  economic_burden: "Economic Burden",
  treatment_landscape: "Treatment Landscape",
  guidelines: "Guidelines",
  market_intelligence: "Market Intelligence",
  synthesis: "Synthesis",
  barrier_identification: "Barrier Identification",
  standard_of_care: "Standard of Care",
  gap_identification: "Gap Identification",
  framework_mapping: "Framework Mapping",
  format_design: "Format Design",
  innovation_section: "Innovation Section",
  protocol_design: "Protocol Design",
  audience_strategy: "Audience Strategy",
  package_assembly: "Package Assembly",
};

function preview(text: string, maxLen = 80): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trimEnd() + "...";
}

interface VsTabProps {
  state: ThreadState | null;
}

export function VsTab({ state }: VsTabProps) {
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  if (!state || Object.keys(state.vsDistributions).length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No VS distributions available
      </div>
    );
  }

  const entries = Object.entries(state.vsDistributions);

  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="grid grid-cols-[1fr_2fr_80px_80px_60px_60px] gap-2 px-3 py-2 text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
        <span>Step</span>
        <span>Selected Approach</span>
        <span className="text-right">Confidence</span>
        <span className="text-right">Runner-Up</span>
        <span className="text-right">Spread</span>
        <span>Dist.</span>
      </div>

      {entries.map(([stepName, dist]: [string, VsDistribution]) => {
        const sorted = [...dist.candidates].sort((a, b) => b.probability - a.probability);
        const selected = dist.selectedIndex >= 0 ? dist.candidates[dist.selectedIndex] : sorted[0];
        const runnerUp = sorted.length > 1 ? sorted[1] : null;
        const spread = runnerUp && selected
          ? (selected.probability - runnerUp.probability).toFixed(3)
          : "\u2014";
        const isExpanded = expandedStep === stepName;

        return (
          <div key={stepName}>
            <button
              onClick={() => setExpandedStep(isExpanded ? null : stepName)}
              className="w-full grid grid-cols-[1fr_2fr_80px_80px_60px_60px] gap-2 px-3 py-2.5 text-xs hover:bg-muted/50 rounded-md transition-colors items-center"
            >
              <span className="font-medium text-left truncate">
                {STEP_LABELS[stepName] ?? stepName.replace(/_/g, " ")}
              </span>
              <span className="text-left truncate text-muted-foreground">
                {selected ? preview(selected.content) : "\u2014"}
              </span>
              <span className="text-right font-mono">
                {selected?.probability.toFixed(3) ?? "\u2014"}
              </span>
              <span className="text-right font-mono text-muted-foreground">
                {runnerUp?.probability.toFixed(3) ?? "\u2014"}
              </span>
              <span className="text-right font-mono">{spread}</span>
              <VsSparkline scores={dist.candidates.map((c) => c.probability)} />
            </button>

            {isExpanded && (
              <div className="mx-3 mb-2 p-3 rounded-md bg-muted/30 space-y-2">
                <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
                  All Candidates ({dist.candidates.length})
                </p>
                {sorted.map((candidate, i) => (
                  <div
                    key={i}
                    className={`flex justify-between text-[11px] px-2 py-1.5 rounded ${
                      selected && candidate.probability === selected.probability
                        ? "bg-primary/10 font-medium"
                        : ""
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-muted-foreground line-clamp-2">
                        {candidate.content}
                      </p>
                    </div>
                    <span className="font-mono ml-4 shrink-0">
                      {candidate.probability.toFixed(4)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
