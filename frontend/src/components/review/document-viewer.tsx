"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { MessageCirclePlus } from "lucide-react";
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
  comments,
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
    <div className="relative flex-1 overflow-auto">
      <div
        ref={containerRef}
        onMouseUp={onMouseUp}
        className="prose prose-sm dark:prose-invert max-w-none p-6 select-text cursor-text"
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>

      {showCommentPopover && pendingSelection && (
        <div
          ref={popoverRef}
          className="fixed z-50 bg-surface border border-border rounded-lg shadow-lg p-3 w-72"
          style={{
            top: pendingSelection.rect.bottom + 8,
            left: Math.min(
              pendingSelection.rect.left,
              window.innerWidth - 300,
            ),
          }}
        >
          <p className="text-xs text-muted-foreground mb-2 truncate">
            &quot;{pendingSelection.text.slice(0, 60)}
            {pendingSelection.text.length > 60 ? "..." : ""}&quot;
          </p>
          <textarea
            value={commentInput}
            onChange={(e) => setCommentInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Add your comment..."
            className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-dhg-purple resize-none"
            rows={2}
            autoFocus
          />
          <div className="flex gap-2 mt-2">
            <Button size="sm" onClick={handleSubmitComment} disabled={!commentInput.trim()}>
              <MessageCirclePlus className="h-3 w-3 mr-1" />
              Comment
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                onClearSelection();
                setShowCommentPopover(false);
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
