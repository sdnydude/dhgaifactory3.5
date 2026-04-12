"use client";

import { useEffect, useCallback, useRef } from "react";
import { RefreshCw, AlertCircle } from "lucide-react";
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
  if (diffMin < 60) return `${diffMin} min`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr} hr`;
  return `${Math.floor(diffHr / 24)} d`;
}

function formatIssueNumber(i: number): string {
  return String(i + 1).padStart(2, "0");
}

function formatTodayMasthead(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
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
    <div className="flex h-full overflow-hidden bg-background">
      {/* ====================================================================
          MASTER — The index (left rail, journal TOC)
          ==================================================================== */}
      <aside className="w-[22rem] shrink-0 flex flex-col border-r border-border">
        {/* Masthead */}
        <header className="px-7 pt-7 pb-5 border-b-[3px] border-double border-foreground/85">
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-mono-editorial small-caps text-[10px] text-muted-foreground">
              Vol. I · № {reviews.length.toString().padStart(2, "0")}
            </span>
            <button
              onClick={fetchReviews}
              disabled={loading}
              aria-label="Refresh reviews"
              className="h-6 w-6 inline-flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            >
              <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
            </button>
          </div>
          <h1
            className="font-display italic font-semibold text-foreground leading-[0.9] mt-1.5"
            style={{
              fontSize: "2.7rem",
              fontVariationSettings: '"SOFT" 80, "opsz" 144',
              letterSpacing: "-0.02em",
            }}
          >
            The&nbsp;Inbox
          </h1>
          <p className="font-serif-body italic text-[11px] text-muted-foreground mt-1.5 tracking-wide">
            A Register of Manuscripts Awaiting Editorial Review
          </p>
          <p className="font-mono-editorial text-[9.5px] small-caps text-muted-foreground/80 mt-2">
            {formatTodayMasthead()}
          </p>
        </header>

        {error && (
          <div className="mx-5 mt-4 flex items-start gap-2 border border-destructive/40 bg-destructive/5 px-3 py-2 font-serif-body text-[11px] text-destructive">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {isDemo && (
          <div className="mx-5 mt-4 border-l-2 border-[color:var(--color-dhg-orange)] pl-3 py-1.5 font-serif-body italic text-[11px] text-muted-foreground">
            Specimen issue. Live manuscripts will supersede these entries as
            agents surface review gates.
          </div>
        )}

        <ScrollArea className="flex-1">
          {loading && reviews.length === 0 ? (
            <div className="flex items-center justify-center py-16 font-serif-body italic text-sm text-muted-foreground">
              <RefreshCw className="h-3 w-3 animate-spin mr-2" />
              Assembling the issue…
            </div>
          ) : reviews.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
              <div
                className="font-display text-[2.8rem] text-muted-foreground/30 leading-none"
                style={{ fontVariationSettings: '"SOFT" 100, "opsz" 144' }}
              >
                ❦
              </div>
              <p className="mt-3 font-serif-body italic text-sm text-muted-foreground">
                The desk is clear.
              </p>
              <p className="mt-1 font-mono-editorial text-[9.5px] small-caps text-muted-foreground/70">
                No pending reviews
              </p>
            </div>
          ) : (
            <ol className="px-5 py-3">
              {reviews.map((review, i) => {
                const isSelected = selectedReviewId === review.threadId;
                return (
                  <li
                    key={review.threadId}
                    className="issue-enter"
                    style={{ animationDelay: `${i * 55}ms` }}
                  >
                    <button
                      onClick={() => selectReview(review.threadId)}
                      className={cn(
                        "group relative w-full text-left py-4 pl-4 pr-2 border-t border-border transition-all",
                        i === reviews.length - 1 && "border-b",
                        isSelected
                          ? "bg-[color:var(--color-dhg-orange)]/[0.04]"
                          : "hover:bg-foreground/[0.025]",
                      )}
                    >
                      {/* Orange selection rule */}
                      <span
                        aria-hidden
                        className={cn(
                          "absolute left-0 top-0 bottom-0 w-[3px] bg-[color:var(--color-dhg-orange)] transition-all",
                          isSelected ? "opacity-100" : "opacity-0 group-hover:opacity-40",
                        )}
                      />

                      <div className="flex items-baseline justify-between gap-3">
                        <span
                          className="font-display text-[10px] small-caps text-muted-foreground tabular-nums"
                          style={{ fontVariationSettings: '"SOFT" 40, "opsz" 8' }}
                        >
                          № {formatIssueNumber(i)}
                        </span>
                        <span className="font-mono-editorial text-[9px] small-caps text-muted-foreground/70">
                          {formatTimeAgo(review.createdAt)} ago
                        </span>
                      </div>
                      <h3
                        className="font-display italic text-[1.05rem] text-foreground mt-1 leading-tight"
                        style={{ fontVariationSettings: '"SOFT" 60, "opsz" 36' }}
                      >
                        {GRAPH_LABELS[review.graphId] ?? review.graphId}
                      </h3>
                      <p className="font-serif-body text-[11.5px] text-muted-foreground mt-1 leading-snug">
                        {review.currentStep}
                      </p>
                      <p className="font-mono-editorial text-[9px] text-muted-foreground/60 mt-1.5">
                        THREAD {review.threadId.slice(0, 8).toUpperCase()}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ol>
          )}
        </ScrollArea>

        {/* Colophon footer */}
        <footer className="px-7 py-3 border-t border-border">
          <p className="font-mono-editorial text-[9px] small-caps text-muted-foreground/60 text-center">
            Set in Fraunces · Source Serif · IBM Plex Mono
          </p>
        </footer>
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
              <div className="py-24 text-center font-serif-body italic text-muted-foreground">
                No manuscript available for this thread.
              </div>
            )}
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center max-w-md px-8">
              <div
                className="font-display italic text-[6rem] text-foreground/10 leading-none"
                style={{ fontVariationSettings: '"SOFT" 100, "opsz" 144' }}
              >
                ℵ
              </div>
              <p
                className="mt-4 font-display italic text-2xl text-foreground"
                style={{ fontVariationSettings: '"SOFT" 60, "opsz" 72' }}
              >
                Select a manuscript
              </p>
              <p className="mt-3 font-serif-body text-[13px] text-muted-foreground leading-relaxed">
                Each entry in the register represents a LangGraph agent awaiting
                your editorial verdict. Manuscripts are collected on a thirty
                second interval.
              </p>
              <p className="mt-6 font-mono-editorial small-caps text-[10px] text-muted-foreground/70">
                — The editors
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
