"use client";

import { useState } from "react";
import { DocumentViewer } from "./document-viewer";
import { CommentsSidebar } from "./comments-sidebar";
import { MetricsBar } from "./metrics-bar";
import { DecisionBar } from "./decision-bar";
import { useAnnotations } from "./use-annotations";
import type { ReviewPayload, ResumeValue, DocumentSection } from "./types";

interface ReviewPanelProps {
  payload: ReviewPayload;
  onSubmit: (value: ResumeValue) => void;
  isLoading: boolean;
}

export function ReviewPanel({ payload, onSubmit, isLoading }: ReviewPanelProps) {
  const documents = buildDocumentSections(payload.document);
  const [activeDocIndex, setActiveDocIndex] = useState(0);
  const activeDoc = documents[activeDocIndex];

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

  return (
    <div className="flex flex-col border border-border rounded-lg overflow-hidden bg-background h-[70vh]">
      <MetricsBar metrics={payload.metrics} reviewRound={payload.review_round} />

      {documents.length > 1 && (
        <div className="flex border-b border-border">
          {documents.map((doc, i) => (
            <button
              key={doc.id}
              onClick={() => setActiveDocIndex(i)}
              className={`px-4 py-2 text-xs font-medium transition-colors ${
                i === activeDocIndex
                  ? "border-b-2 border-dhg-purple text-dhg-purple"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {doc.label}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <DocumentViewer
          content={activeDoc?.content ?? ""}
          comments={comments.filter((c) => !c.documentId || c.documentId === activeDoc?.id)}
          pendingSelection={pendingSelection}
          containerRef={containerRef}
          onMouseUp={handleMouseUp}
          onAddComment={addComment}
          onClearSelection={clearPendingSelection}
        />

        <div className="hidden md:block w-72 border-l border-border overflow-auto">
          <CommentsSidebar
            comments={comments}
            onRemove={removeComment}
            onUpdate={updateComment}
            onScrollTo={handleScrollToComment}
          />
        </div>
      </div>

      <div className="md:hidden border-t border-border max-h-48 overflow-auto">
        <CommentsSidebar
          comments={comments}
          onRemove={removeComment}
          onUpdate={updateComment}
          onScrollTo={handleScrollToComment}
        />
      </div>

      <DecisionBar comments={comments} onSubmit={onSubmit} isLoading={isLoading} />
    </div>
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
