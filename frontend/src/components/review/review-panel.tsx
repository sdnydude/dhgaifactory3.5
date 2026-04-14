"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { DocumentViewer } from "./document-viewer";
import { CommentsSidebar } from "./comments-sidebar";
import { MetricsBar } from "./metrics-bar";
import { DecisionBar } from "./decision-bar";
import { useAnnotations } from "./use-annotations";
import { VSAlternatives } from "./vs-alternatives";
import { Button } from "@/components/ui/button";
import { useReviewStore } from "@/stores/review-store";
import { downloadDocument } from "@/lib/exportApi";
import type { ReviewPayloadWithVS, ResumeValue, DocumentSection } from "./types";

interface ReviewPanelProps {
  payload: ReviewPayloadWithVS;
  onSubmit: (value: ResumeValue) => void;
  isLoading: boolean;
}

const RECIPE_LABELS: Record<string, string> = {
  needs_package: "The Needs Package",
  curriculum_package: "The Curriculum Package",
  grant_package: "The Grant Package",
  full_pipeline: "The Full Pipeline",
};

export function ReviewPanel({ payload, onSubmit, isLoading }: ReviewPanelProps) {
  const documents = buildDocumentSections(payload.document);
  const [activeDocIndex, setActiveDocIndex] = useState(0);
  const activeDoc = documents[activeDocIndex];
  const selectedThreadId = useReviewStore((s) => s.selectedReviewId);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleDownload = async () => {
    const threadId = selectedThreadId;
    if (!threadId) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      await downloadDocument(threadId, payload.project_name ?? "document");
    } catch (err) {
      console.error("Document download failed", err);
      setDownloadError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  };

  const {
    comments,
    pendingSelection,
    containerRef,
    handleMouseUp,
    addComment,
    removeComment,
    updateComment,
    clearPendingSelection,
  } = useAnnotations(activeDoc?.id);

  const handleScrollToComment = (_comment: typeof comments[number]) => {
    if (containerRef.current) {
      const textLength = containerRef.current.textContent?.length ?? 1;
      const scrollRatio = _comment.startOffset / textLength;
      const scrollTarget = containerRef.current.scrollHeight * scrollRatio;
      containerRef.current.scrollTo({ top: scrollTarget - 100, behavior: "smooth" });
    }
  };

  const recipeLabel = RECIPE_LABELS[payload.recipe] ?? payload.recipe;

  return (
    <article className="mt-10 border-t-[3px] border-double border-foreground/85 pt-8">
      {/* Manuscript masthead */}
      <header className="mb-6">
        <div className="flex items-baseline justify-between gap-4 border-b border-border pb-2 mb-5">
          <span className="font-mono-editorial small-caps text-[10px] text-muted-foreground">
            Manuscript for review
          </span>
          <div className="flex items-center gap-4">
            <span className="font-mono-editorial small-caps text-[10px] text-muted-foreground tabular-nums">
              Round {payload.review_round + 1} of III
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleDownload}
              disabled={downloading || !selectedThreadId}
              aria-label="Download document"
              className="no-print h-7 gap-1.5 text-[11px]"
            >
              <Download className="h-3.5 w-3.5" aria-hidden />
              {downloading ? "Preparing…" : "Document"}
            </Button>
            {downloadError && (
              <span
                role="alert"
                className="no-print font-mono-editorial text-[10px] text-destructive"
              >
                {downloadError}
              </span>
            )}
          </div>
        </div>
        <p
          className="font-display italic text-foreground/60 text-sm"
          style={{ fontVariationSettings: '"SOFT" 60, "opsz" 24' }}
        >
          Being a document of the
        </p>
        <h1
          className="font-display font-semibold text-foreground leading-[0.95] mt-0.5"
          style={{
            fontSize: "3rem",
            fontVariationSettings: '"SOFT" 70, "opsz" 144',
            letterSpacing: "-0.022em",
          }}
        >
          {recipeLabel}
        </h1>
        <p className="mt-3 font-serif-body text-[14px] text-muted-foreground">
          Prepared for{" "}
          <span className="italic text-foreground">
            &ldquo;{payload.project_name}&rdquo;
          </span>{" "}
          · Current step:{" "}
          <span className="font-mono-editorial text-[11px]">
            {payload.current_step}
          </span>
        </p>
      </header>

      {/* Section tabs (if multi-document) */}
      {documents.length > 1 && (
        <nav className="flex flex-wrap gap-0 border-b border-border mb-5">
          {documents.map((doc, i) => {
            const active = i === activeDocIndex;
            return (
              <button
                key={doc.id}
                onClick={() => setActiveDocIndex(i)}
                className={`relative px-4 py-2.5 font-display text-[13px] italic transition-colors ${
                  active
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                style={{ fontVariationSettings: '"SOFT" 50, "opsz" 36' }}
              >
                <span className="font-mono-editorial small-caps text-[9px] text-muted-foreground mr-2 tabular-nums">
                  § {String(i + 1).padStart(2, "0")}
                </span>
                {doc.label}
                {active && (
                  <span
                    aria-hidden
                    className="absolute -bottom-px left-0 right-0 h-[2.5px] bg-[color:var(--color-dhg-orange)]"
                  />
                )}
              </button>
            );
          })}
        </nav>
      )}

      {/* Footnote metrics bar */}
      <MetricsBar metrics={payload.metrics} reviewRound={payload.review_round} />

      {/* Body + marginalia */}
      <div className="flex gap-8 mt-6">
        <div className="flex-1 min-w-0">
          <DocumentViewer
            content={activeDoc?.content ?? ""}
            comments={comments.filter((c) => !c.documentId || c.documentId === activeDoc?.id)}
            pendingSelection={pendingSelection}
            containerRef={containerRef}
            onMouseUp={handleMouseUp}
            onAddComment={addComment}
            onClearSelection={clearPendingSelection}
          />
        </div>

        <aside className="hidden lg:block w-64 shrink-0 border-l border-border pl-5">
          <p
            className="font-display italic text-[11px] small-caps text-muted-foreground mb-3 pb-2 border-b border-border"
            style={{ fontVariationSettings: '"SOFT" 40, "opsz" 14' }}
          >
            Marginalia
          </p>
          <CommentsSidebar
            comments={comments}
            onRemove={removeComment}
            onUpdate={updateComment}
            onScrollTo={handleScrollToComment}
          />
        </aside>
      </div>

      {/* VS alternatives — set as a separate numbered section */}
      {payload.vs_distributions && activeDoc && payload.vs_distributions[activeDoc.id] && (
        <section className="mt-10 pt-6 border-t border-border">
          <h2
            className="font-display italic text-xl text-foreground mb-4"
            style={{ fontVariationSettings: '"SOFT" 50, "opsz" 72' }}
          >
            <span className="font-mono-editorial small-caps text-[10px] text-muted-foreground mr-2 not-italic tabular-nums">
              Appendix A ·
            </span>
            Alternative phrasings considered
          </h2>
          <VSAlternatives
            distribution={payload.vs_distributions[activeDoc.id]}
            agentLabel={activeDoc.label}
          />
        </section>
      )}

      {/* Mobile marginalia */}
      <div className="lg:hidden mt-8 pt-6 border-t border-border">
        <p
          className="font-display italic text-[11px] small-caps text-muted-foreground mb-3"
          style={{ fontVariationSettings: '"SOFT" 40, "opsz" 14' }}
        >
          Marginalia
        </p>
        <CommentsSidebar
          comments={comments}
          onRemove={removeComment}
          onUpdate={updateComment}
          onScrollTo={handleScrollToComment}
        />
      </div>

      {/* Editorial stamps */}
      <div className="mt-10">
        <DecisionBar comments={comments} onSubmit={onSubmit} isLoading={isLoading} />
      </div>
    </article>
  );
}

function buildDocumentSections(
  docs: Record<string, string>,
): DocumentSection[] {
  const LABELS: Record<string, string> = {
    needs_assessment: "Needs Assessment",
    curriculum_design: "Curriculum Design",
    research_protocol: "Research Protocol",
    marketing_plan: "Marketing Plan",
    grant_package: "Grant Package",
  };

  return Object.entries(docs)
    .filter(([, content]) => content && content.trim())
    .map(([id, content]) => ({
      id,
      label: LABELS[id] ?? id,
      content,
    }));
}
