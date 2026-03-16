"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import { OutputSlideOver } from "./output-slide-over";
import { OUTPUT_KEYS } from "@/lib/agentsApi";
import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

const OUTPUT_LABELS: Record<string, string> = {
  research_output: "Research & Literature",
  clinical_output: "Clinical Practice",
  gap_analysis_output: "Gap Analysis",
  learning_objectives_output: "Learning Objectives",
  needs_assessment_output: "Needs Assessment",
  curriculum_output: "Curriculum Design",
  protocol_output: "Research Protocol",
  marketing_output: "Marketing Plan",
  grant_package_output: "Grant Package",
  prose_quality_pass_1: "Prose QA Pass 1",
  prose_quality_pass_2: "Prose QA Pass 2",
  compliance_result: "Compliance Review",
};

function textPreview(text: string, maxLen = 150): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trimEnd() + "...";
}

function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

interface OutputsTabProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

export function OutputsTab({ agent, state }: OutputsTabProps) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  if (!state || state.completedOutputs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No completed outputs yet
      </div>
    );
  }

  // Order by pipeline sequence
  const ordered = OUTPUT_KEYS.filter((k) => state.completedOutputs.includes(k));

  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        {ordered.map((key) => {
          const content = state.outputContents[key] ?? "";
          const label = OUTPUT_LABELS[key] ?? key.replace(/_/g, " ");
          const words = wordCount(content);

          return (
            <button
              key={key}
              onClick={() => setSelectedKey(key)}
              className="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors text-left"
            >
              <FileText className="h-4 w-4 text-green-600 dark:text-green-400 shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-xs font-medium">{label}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {words.toLocaleString()} words
                </p>
                {content && (
                  <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">
                    {textPreview(content)}
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>

      <OutputSlideOver
        open={selectedKey !== null}
        onClose={() => setSelectedKey(null)}
        outputKey={selectedKey ?? ""}
        content={selectedKey ? (state.outputContents[selectedKey] ?? "") : ""}
        projectId={state.projectId}
        threadCreatedAt={agent.createdAt}
      />
    </>
  );
}
