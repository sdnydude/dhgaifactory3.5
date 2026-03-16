"use client";

import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";
import { getPreviousRunOutput } from "@/lib/agentsApi";

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

interface OutputSlideOverProps {
  open: boolean;
  onClose: () => void;
  outputKey: string;
  content: string;
  projectId: string;
  threadCreatedAt: string;
}

function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

export function OutputSlideOver({
  open,
  onClose,
  outputKey,
  content,
  projectId,
  threadCreatedAt,
}: OutputSlideOverProps) {
  const [showDiff, setShowDiff] = useState(false);
  const [previousContent, setPreviousContent] = useState<string | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffChecked, setDiffChecked] = useState(false);

  useEffect(() => {
    if (!open) {
      setShowDiff(false);
      setPreviousContent(null);
      setDiffChecked(false);
      return;
    }

    setDiffLoading(true);
    getPreviousRunOutput(projectId, threadCreatedAt, outputKey)
      .then((prev) => {
        setPreviousContent(prev);
        setDiffChecked(true);
      })
      .catch(() => {
        setPreviousContent(null);
        setDiffChecked(true);
      })
      .finally(() => setDiffLoading(false));
  }, [open, projectId, threadCreatedAt, outputKey]);

  const label = OUTPUT_LABELS[outputKey] ?? outputKey.replace(/_/g, " ");
  const words = wordCount(content);

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-[60vw] sm:max-w-none overflow-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center justify-between">
            <span>{label}</span>
            <div className="flex items-center gap-3 text-xs font-normal text-muted-foreground">
              <span>{words.toLocaleString()} words</span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-[11px]"
                      disabled={!diffChecked || previousContent === null}
                      onClick={() => setShowDiff(!showDiff)}
                    >
                      {showDiff ? "Hide Diff" : "Compare"}
                    </Button>
                  </TooltipTrigger>
                  {diffChecked && previousContent === null && (
                    <TooltipContent>No previous run to compare</TooltipContent>
                  )}
                </Tooltip>
              </TooltipProvider>
            </div>
          </SheetTitle>
        </SheetHeader>

        <div className="mt-4">
          {showDiff && previousContent ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] text-muted-foreground font-medium uppercase mb-2">
                  Current Run
                </p>
                <div className="text-sm leading-relaxed whitespace-pre-wrap font-[Inter]">
                  {content.split("\n").map((line, i) => {
                    const prevLines = previousContent.split("\n");
                    const isNew = !prevLines.includes(line) && line.trim() !== "";
                    return (
                      <div
                        key={i}
                        className={isNew ? "bg-green-500/10 px-1 -mx-1 rounded" : ""}
                      >
                        {line || "\u00A0"}
                      </div>
                    );
                  })}
                </div>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground font-medium uppercase mb-2">
                  Previous Run
                </p>
                <div className="text-sm leading-relaxed whitespace-pre-wrap font-[Inter]">
                  {previousContent.split("\n").map((line, i) => {
                    const currentLines = content.split("\n");
                    const isRemoved = !currentLines.includes(line) && line.trim() !== "";
                    return (
                      <div
                        key={i}
                        className={isRemoved ? "bg-red-500/10 px-1 -mx-1 rounded" : ""}
                      >
                        {line || "\u00A0"}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm leading-relaxed whitespace-pre-wrap font-[Inter]">
              {content}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
