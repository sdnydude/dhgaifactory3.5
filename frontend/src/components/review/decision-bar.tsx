"use client";

import { Button } from "@/components/ui/button";
import { CheckCircle, RotateCcw, XCircle } from "lucide-react";
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

  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3 border-t border-border bg-muted/30">
      <span className="text-xs text-muted-foreground">
        {comments.length} comment{comments.length !== 1 ? "s" : ""} attached
      </span>
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => handleDecision("approved")}
          disabled={isLoading}
          className="bg-green-600 hover:bg-green-700 text-white"
        >
          <CheckCircle className="h-4 w-4 mr-1" />
          Approve
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => handleDecision("revision")}
          disabled={isLoading}
        >
          <RotateCcw className="h-4 w-4 mr-1" />
          Request Revision
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => handleDecision("rejected")}
          disabled={isLoading}
          className="border-red-300 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950"
        >
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      </div>
    </div>
  );
}
