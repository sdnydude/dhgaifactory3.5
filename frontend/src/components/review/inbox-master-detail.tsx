"use client";

import { useEffect, useCallback, useRef } from "react";
import { RefreshCw, AlertCircle, Inbox, FileText } from "lucide-react";
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
  if (diffMin < 60) return `${diffMin} min`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr} hr`;
  return `${Math.floor(diffHr / 24)} d`;
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
    } finally {
      setLoading(false);
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
    <div className="flex flex-col h-full overflow-hidden bg-background">
      {/* Standard page header — matches /monitoring pattern */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <h1 className="text-lg font-semibold">Inbox</h1>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            {reviews.length} pending {reviews.length === 1 ? "review" : "reviews"}
          </span>
          <button
            onClick={fetchReviews}
            disabled={loading}
            aria-label="Refresh reviews"
            className="h-8 w-8 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
      {/* ====================================================================
          MASTER — The index (left rail)
          ==================================================================== */}
      <aside className="w-[22rem] shrink-0 flex flex-col border-r border-border">
        {error && (
          <div className="mx-5 mt-4 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {isDemo && (
          <div className="mx-5 mt-4 rounded-md border-l-2 border-[color:var(--color-dhg-orange)] bg-muted/40 pl-3 pr-2 py-1.5 text-xs text-muted-foreground">
            Sample data. Real reviews will replace these as agents reach review gates.
          </div>
        )}

        <ScrollArea className="flex-1">
          {loading && reviews.length === 0 ? (
            <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
              <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" />
              Loading reviews…
            </div>
          ) : reviews.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
              <Inbox className="h-10 w-10 text-muted-foreground/40" />
              <p className="mt-3 text-sm font-medium text-foreground">
                No pending reviews
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Reviews appear here when agents reach a human review gate.
              </p>
            </div>
          ) : (
            <ul className="py-1">
              {reviews.map((review, i) => {
                const isSelected = selectedReviewId === review.threadId;
                return (
                  <li key={review.threadId}>
                    <button
                      onClick={() => selectReview(review.threadId)}
                      className={cn(
                        "group relative w-full text-left px-5 py-3 border-b border-border transition-colors",
                        i === 0 && "border-t",
                        isSelected
                          ? "bg-muted"
                          : "hover:bg-muted/50",
                      )}
                    >
                      <span
                        aria-hidden
                        className={cn(
                          "absolute left-0 top-0 bottom-0 w-[3px] bg-[color:var(--color-dhg-orange)] transition-opacity",
                          isSelected ? "opacity-100" : "opacity-0",
                        )}
                      />

                      <div className="flex items-baseline justify-between gap-3">
                        <h3 className="text-sm font-medium text-foreground leading-tight truncate">
                          {GRAPH_LABELS[review.graphId] ?? review.graphId}
                        </h3>
                        <span className="shrink-0 text-[10px] text-muted-foreground tabular-nums">
                          {formatTimeAgo(review.createdAt)}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground truncate">
                        {review.currentStep}
                      </p>
                      <p className="mt-1 font-mono text-[10px] text-muted-foreground/70">
                        {review.threadId.slice(0, 8)}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </ScrollArea>
      </aside>

      {/* ====================================================================
          DETAIL — The manuscript under review
          ==================================================================== */}
      <main className="flex-1 overflow-auto">
        {selectedReview ? (
          <div className="mx-auto max-w-[78rem] px-10 py-10">
            {/* Publisher's Note (AI reflection) */}
            {selectedReview.payload && (
              <ReflectionPanel
                metrics={selectedReview.payload.metrics}
                recipe={selectedReview.payload.recipe}
                reviewRound={selectedReview.payload.review_round}
              />
            )}

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
              <div className="py-24 text-center text-sm text-muted-foreground">
                No content available for this thread.
              </div>
            )}
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center max-w-sm px-8">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground/30" />
              <p className="mt-4 text-lg font-semibold text-foreground">
                Select a review
              </p>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                Choose a pending review from the list to see its content and
                approve, revise, or reject it. The list refreshes every 30 seconds.
              </p>
            </div>
          </div>
        )}
      </main>
      </div>
    </div>
  );
}
