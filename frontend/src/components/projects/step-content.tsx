"use client";

import { Loader2, AlertTriangle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AgentOutput } from "@/types/cme";
import type { StepStatus } from "./pipeline-step";

const DOCUMENT_KEYS: Record<string, string> = {
  research: "research_document",
  clinical: "clinical_practice_document",
  gap_analysis: "gap_analysis_document",
  learning_objectives: "learning_objectives_document",
  needs_assessment: "complete_document",
  curriculum: "curriculum_document",
  protocol: "protocol_document",
  marketing: "marketing_document",
  grant_writer: "complete_document_markdown",
  prose_quality_1: "summary",
  prose_quality_2: "summary",
  compliance: "compliance_report",
};

function extractDocument(agentName: string, output: AgentOutput): string | null {
  if (output.document_text && output.document_text.length > 10) return output.document_text;
  const content = output.content;
  const key = DOCUMENT_KEYS[agentName];
  if (key && typeof content[key] === "string") return content[key] as string;
  for (const k of Object.keys(content)) {
    if (k.endsWith("_document") && typeof content[k] === "string") return content[k] as string;
  }
  if (typeof content.document === "string") return content.document as string;
  if (typeof content.complete_document === "string") return content.complete_document as string;
  return null;
}

interface StepContentProps {
  stepId: string;
  stepLabel: string;
  status: StepStatus;
  output: AgentOutput | null;
}

export function StepContent({ stepId, stepLabel, status, output }: StepContentProps) {
  if (status === "error") {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertTriangle className="h-8 w-8 text-destructive mb-3" />
        <p className="text-sm font-medium">{stepLabel}</p>
        <p className="text-xs text-destructive">Agent failed</p>
        {output?.content?.errors ? (
          <pre className="mt-4 text-xs bg-destructive/10 text-destructive p-3 rounded-md max-w-lg text-left overflow-auto max-h-[200px]">
            {JSON.stringify(output.content.errors, null, 2)}
          </pre>
        ) : null}
      </div>
    );
  }

  if (status === "active") {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
        <p className="text-sm font-medium">{stepLabel}</p>
        <p className="text-xs text-muted-foreground">Agent is running...</p>
      </div>
    );
  }

  if (status === "pending") {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-sm text-muted-foreground">{stepLabel}</p>
        <p className="text-xs text-muted-foreground">Waiting for previous steps to complete</p>
      </div>
    );
  }

  if (!output) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-sm text-muted-foreground">No output available for {stepLabel}</p>
      </div>
    );
  }

  const doc = extractDocument(stepId, output);
  const wordCount = typeof output.content.word_count === "number" ? output.content.word_count : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{stepLabel}</h3>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {wordCount !== null ? <span>{wordCount.toLocaleString()} words</span> : null}
          {output.quality_score !== null ? (
            <span>Quality: {Math.round(output.quality_score * 100)}%</span>
          ) : null}
        </div>
      </div>
      {doc ? (
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc}</ReactMarkdown>
        </div>
      ) : (
        <pre className="text-xs bg-muted p-4 rounded-md overflow-auto max-h-[600px]">
          {JSON.stringify(output.content, null, 2)}
        </pre>
      )}
    </div>
  );
}
