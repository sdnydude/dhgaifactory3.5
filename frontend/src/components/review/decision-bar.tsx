"use client";

import type { ReviewComment, ResumeValue } from "./types";

interface DecisionBarProps {
  comments: ReviewComment[];
  onSubmit: (value: ResumeValue) => void;
  isLoading: boolean;
}

export function DecisionBar({ comments, onSubmit, isLoading }: DecisionBarProps) {
  const handleDecision = (decision: ResumeValue["decision"]) => {
    onSubmit({ decision, comments });
  };

  const annotationCount = comments.length;

  return (
    <section className="pt-8 mt-2">
      <div className="flex items-baseline justify-between border-b border-border pb-3 mb-6">
        <p
          className="font-display italic text-[10px] small-caps text-muted-foreground"
          style={{ fontVariationSettings: '"SOFT" 40, "opsz" 10' }}
        >
          The editorial verdict
        </p>
        <p className="font-mono-editorial small-caps text-[10px] text-muted-foreground tabular-nums">
          {annotationCount} annotation{annotationCount !== 1 ? "s" : ""} attached
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-x-7 gap-y-5">
        <p
          className="font-serif-body italic text-[13px] text-muted-foreground max-w-xs leading-snug"
        >
          Render judgment. The manuscript and your annotations will be returned
          to the agent graph for its next action.
        </p>

        <div className="flex flex-wrap items-center gap-5 ml-auto">
          <button
            type="button"
            onClick={() => handleDecision("approved")}
            disabled={isLoading}
            className="stamp-btn stamp-approved"
            aria-label="Approve manuscript"
          >
            Approved
          </button>
          <button
            type="button"
            onClick={() => handleDecision("revision")}
            disabled={isLoading}
            className="stamp-btn stamp-revision"
            aria-label="Request revision"
          >
            Revise
          </button>
          <button
            type="button"
            onClick={() => handleDecision("rejected")}
            disabled={isLoading}
            className="stamp-btn stamp-rejected"
            aria-label="Reject manuscript"
          >
            Rejected
          </button>
        </div>
      </div>

      {isLoading && (
        <p className="mt-5 font-serif-body italic text-[12px] text-muted-foreground animate-pulse">
          Returning manuscript to the graph…
        </p>
      )}
    </section>
  );
}
