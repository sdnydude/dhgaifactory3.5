"use client";

import { Button } from "@/components/ui/button";
import { Trash2, MessageSquare } from "lucide-react";
import type { ReviewComment } from "./types";

interface CommentsSidebarProps {
  comments: ReviewComment[];
  onRemove: (id: string) => void;
  onUpdate: (id: string, newText: string) => void;
  onScrollTo: (comment: ReviewComment) => void;
}

export function CommentsSidebar({
  comments,
  onRemove,
  onUpdate,
  onScrollTo,
}: CommentsSidebarProps) {
  if (comments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <MessageSquare className="h-8 w-8 mb-2 opacity-40" />
        <p className="text-xs">No comments yet</p>
        <p className="text-xs mt-1">Select text in the document to add comments</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 p-3">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        Comments ({comments.length})
      </h3>
      {comments.map((comment, index) => (
        <div
          key={comment.id}
          className="border border-border rounded-md p-2.5 text-sm hover:border-dhg-purple/50 transition-colors cursor-pointer"
          onClick={() => onScrollTo(comment)}
        >
          <div className="flex items-start justify-between gap-2">
            <span className="text-xs font-medium text-dhg-purple">
              #{index + 1}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 w-5 p-0 text-muted-foreground hover:text-red-500"
              onClick={(e) => {
                e.stopPropagation();
                onRemove(comment.id);
              }}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-1 italic truncate">
            &quot;{comment.selectedText.slice(0, 80)}
            {comment.selectedText.length > 80 ? "..." : ""}&quot;
          </p>
          <textarea
            value={comment.comment}
            onChange={(e) => onUpdate(comment.id, e.target.value)}
            onClick={(e) => e.stopPropagation()}
            className="w-full mt-1.5 rounded border border-border bg-background px-2 py-1 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-dhg-purple resize-none"
            rows={2}
          />
          {comment.documentId && (
            <span className="text-[10px] text-muted-foreground mt-1 block">
              {comment.documentId}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
