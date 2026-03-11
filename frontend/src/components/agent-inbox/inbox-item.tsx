"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, Clock } from "lucide-react";
import { ReviewPanel } from "@/components/review/review-panel";
import type { PendingReview } from "@/lib/inboxApi";
import type { ResumeValue } from "@/components/review/types";

interface InboxItemProps {
  review: PendingReview;
  onAction: (threadId: string, graphId: string, resumeValue: ResumeValue) => void;
  isLoading: boolean;
}

const GRAPH_LABELS: Record<string, string> = {
  needs_package: "Needs Package",
  curriculum_package: "Curriculum Package",
  grant_package: "Grant Package",
  full_pipeline: "Full Pipeline",
  needs_assessment: "Needs Assessment",
  research: "Research",
  clinical_practice: "Clinical Practice",
  gap_analysis: "Gap Analysis",
  learning_objectives: "Learning Objectives",
  curriculum_design: "Curriculum Design",
  research_protocol: "Research Protocol",
  marketing_plan: "Marketing Plan",
  grant_writer: "Grant Writer",
  prose_quality: "Prose Quality",
  compliance_review: "Compliance Review",
};

export function InboxItem({ review, onAction, isLoading }: InboxItemProps) {
  const [expanded, setExpanded] = useState(false);

  const graphLabel = GRAPH_LABELS[review.graphId] ?? review.graphId;
  const timeAgo = formatTimeAgo(review.createdAt);

  const handleSubmit = (resumeValue: ResumeValue) => {
    onAction(review.threadId, review.graphId, resumeValue);
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="border-dhg-purple text-dhg-purple">
              {graphLabel}
            </Badge>
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {timeAgo}
            </span>
          </div>
          <Badge variant="secondary">{review.currentStep}</Badge>
        </div>
        <CardTitle className="text-sm font-medium mt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 hover:text-dhg-purple transition-colors"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            Thread {review.threadId.slice(0, 8)}... — {expanded ? "Collapse" : "Open Review"}
          </button>
        </CardTitle>
      </CardHeader>
      {expanded && review.payload && (
        <CardContent>
          <ReviewPanel
            payload={review.payload}
            onSubmit={handleSubmit}
            isLoading={isLoading}
          />
        </CardContent>
      )}
      {expanded && !review.payload && (
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No review payload available. This interrupt may not contain document data.
          </p>
        </CardContent>
      )}
    </Card>
  );
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}
