"use client";

import { useEffect, useCallback, useRef } from "react";
import { Inbox, RefreshCw, AlertCircle, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ReviewPanel } from "./review-panel";
import { ReflectionPanel } from "./reflection-panel";
import { useReviewStore } from "@/stores/review-store";
import { listPendingReviews, resumeThread } from "@/lib/inboxApi";
import type { ResumeValue } from "./types";
import { cn } from "@/lib/utils";
import { DEMO_REVIEWS, isDemoReview } from "./demo-reviews";

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

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

export function InboxMasterDetail() {
  const {
    reviews,
    selectedReviewId,
    loading,
    error,
    actionLoading,
    setReviews,
    selectReview,
    setLoading,
    setError,
    setActionLoading,
    removeReview,
  } = useReviewStore();

  const demoDismissedRef = useRef(false);

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listPendingReviews();
      if (data.length > 0) {
        demoDismissedRef.current = false;
        setReviews(data);
      } else if (!demoDismissedRef.current) {
        setReviews(DEMO_REVIEWS);
      } else {
        setReviews([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reviews");
    }
  }, [setReviews, setLoading, setError]);

  useEffect(() => {
    fetchReviews();
    const interval = setInterval(fetchReviews, 30_000);
    return () => clearInterval(interval);
  }, [fetchReviews]);

  const selectedReview = reviews.find((r) => r.threadId === selectedReviewId);

  const isDemo = reviews.length > 0 && reviews.every((r) => isDemoReview(r.threadId));

  const handleAction = async (
    threadId: string,
    graphId: string,
    resumeValue: ResumeValue,
  ) => {
    if (isDemoReview(threadId)) {
      removeReview(threadId);
      const remainingDemo = reviews.filter(
        (r) => r.threadId !== threadId && isDemoReview(r.threadId),
      );
      if (remainingDemo.length === 0) {
        demoDismissedRef.current = true;
      }
      return;
    }
    setActionLoading(threadId);
    try {
      await resumeThread(threadId, graphId, resumeValue);
      removeReview(threadId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to process action");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Master list */}
      <div className="w-80 border-r border-border flex flex-col shrink-0">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold">Reviews</h2>
            <Badge variant="secondary" className="text-[10px]">
              {reviews.length}
            </Badge>
          </div>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={fetchReviews} disabled={loading}>
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          </Button>
        </div>

        {error && (
          <div className="mx-3 mt-2 flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            {error}
          </div>
        )}

        {isDemo && (
          <div className="mx-3 mt-2 flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
            <Info className="h-3.5 w-3.5 shrink-0" />
            Sample data — reviews appear when agents reach human review gates
          </div>
        )}

        <ScrollArea className="flex-1">
          {loading && reviews.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground text-sm">
              <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              Loading...
            </div>
          ) : reviews.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <Inbox className="h-10 w-10 mb-2 opacity-40" />
              <p className="text-xs">No pending reviews</p>
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {reviews.map((review) => {
                const isSelected = selectedReviewId === review.threadId;
                return (
                  <button
                    key={review.threadId}
                    onClick={() => selectReview(review.threadId)}
                    className={cn(
                      "w-full text-left rounded-md px-3 py-2.5 transition-colors",
                      isSelected
                        ? "bg-primary/10 border border-primary/20"
                        : "hover:bg-muted border border-transparent",
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <Badge variant="outline" className="text-[10px] border-dhg-purple text-dhg-purple">
                        {GRAPH_LABELS[review.graphId] ?? review.graphId}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground">
                        {formatTimeAgo(review.createdAt)}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {review.currentStep} — Thread {review.threadId.slice(0, 8)}...
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-auto">
        {selectedReview ? (
          <div className="p-4 space-y-4">
            {/* Reflection panel */}
            {selectedReview.payload && (
              <ReflectionPanel
                metrics={selectedReview.payload.metrics}
                recipe={selectedReview.payload.recipe}
                reviewRound={selectedReview.payload.review_round}
              />
            )}

            {/* Full review panel */}
            {selectedReview.payload ? (
              <ReviewPanel
                payload={selectedReview.payload}
                onSubmit={(resumeValue) =>
                  handleAction(
                    selectedReview.threadId,
                    selectedReview.graphId,
                    resumeValue,
                  )
                }
                isLoading={actionLoading === selectedReview.threadId}
              />
            ) : (
              <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
                No review payload available for this thread.
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <Inbox className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm">Select a review from the list</p>
            <p className="text-xs mt-1">
              Reviews appear when agents reach human review gates
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
