"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReviewComment } from "./types";

interface DocumentViewerProps {
  content: string;
  comments: ReviewComment[];
  pendingSelection: {
    text: string;
    startOffset: number;
    endOffset: number;
    rect: DOMRect;
  } | null;
  containerRef: React.RefObject<HTMLDivElement | null>;
  onMouseUp: () => void;
  onAddComment: (comment: string) => void;
  onClearSelection: () => void;
}

export function DocumentViewer({
  content,
  pendingSelection,
  containerRef,
  onMouseUp,
  onAddComment,
  onClearSelection,
}: DocumentViewerProps) {
  const [commentInput, setCommentInput] = useState("");
  const [showCommentPopover, setShowCommentPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (pendingSelection) {
      setShowCommentPopover(true);
      setCommentInput("");
    } else {
      setShowCommentPopover(false);
    }
  }, [pendingSelection]);

  const handleSubmitComment = () => {
    if (!commentInput.trim()) return;
    onAddComment(commentInput.trim());
    setCommentInput("");
    setShowCommentPopover(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmitComment();
    }
    if (e.key === "Escape") {
      onClearSelection();
      setShowCommentPopover(false);
    }
  };

  return (
    <div className="relative">
      <div
        ref={containerRef}
        onMouseUp={onMouseUp}
        className="journal-prose journal-columns drop-cap select-text cursor-text max-w-none"
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>

      {/* Margin-note popover — styled as an editorial annotation */}
      {showCommentPopover && pendingSelection && (
        <div
          ref={popoverRef}
          className="fixed z-50 w-80 bg-[color:var(--background)] shadow-[0_20px_60px_-15px_rgba(50,55,74,0.35)] border border-foreground/25"
          style={{
            top: pendingSelection.rect.bottom + 10,
            left: Math.min(
              pendingSelection.rect.left,
              window.innerWidth - 340,
            ),
          }}
        >
          {/* Paper edge */}
          <div className="absolute inset-x-0 -top-[3px] h-[3px] bg-[color:var(--color-dhg-orange)]" />

          <div className="p-4">
            <p className="font-mono-editorial small-caps text-[9px] text-muted-foreground mb-1.5">
              Marginal note
            </p>
            <blockquote className="font-serif-body italic text-[12px] text-foreground/75 border-l-2 border-[color:var(--color-dhg-orange)] pl-2.5 mb-3 leading-snug">
              &ldquo;{pendingSelection.text.slice(0, 90)}
              {pendingSelection.text.length > 90 ? "…" : ""}&rdquo;
            </blockquote>
            <textarea
              value={commentInput}
              onChange={(e) => setCommentInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Your annotation…"
              className="w-full bg-transparent border border-border font-serif-body italic text-[13px] px-2.5 py-2 focus:outline-none focus:border-[color:var(--color-dhg-orange)] resize-none"
              rows={2}
              autoFocus
            />
            <div className="flex items-center justify-between mt-2.5">
              <button
                onClick={() => {
                  onClearSelection();
                  setShowCommentPopover(false);
                }}
                className="font-mono-editorial small-caps text-[10px] text-muted-foreground hover:text-foreground transition-colors"
              >
                Dismiss
              </button>
              <button
                onClick={handleSubmitComment}
                disabled={!commentInput.trim()}
                className="font-display italic text-[12px] text-foreground border-b border-[color:var(--color-dhg-orange)] hover:text-[color:var(--color-dhg-orange)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                style={{ fontVariationSettings: '"SOFT" 50, "opsz" 14' }}
              >
                Commit note →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
