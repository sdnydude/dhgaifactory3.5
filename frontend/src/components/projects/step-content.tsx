"use client";

import { Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AgentOutput } from "@/types/cme";
import type { StepStatus } from "./pipeline-step";

interface StepContentProps {
  stepId: string;
  stepLabel: string;
  status: StepStatus;
  output: AgentOutput | null;
}

export function StepContent({ stepLabel, status, output }: StepContentProps) {
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

  const doc = output.content.document as string | undefined;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{stepLabel}</h3>
        {output.quality_score !== null && (
          <span className="text-xs text-muted-foreground">
            Quality: {Math.round(output.quality_score * 100)}%
          </span>
        )}
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
