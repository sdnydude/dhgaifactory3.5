"use client";

import { useState, useCallback, useRef } from "react";
import type { ReviewComment } from "./types";

export function useAnnotations(documentId?: string) {
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [pendingSelection, setPendingSelection] = useState<{
    text: string;
    startOffset: number;
    endOffset: number;
    rect: DOMRect;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !containerRef.current) {
      setPendingSelection(null);
      return;
    }

    const range = selection.getRangeAt(0);

    if (!containerRef.current.contains(range.commonAncestorContainer)) {
      setPendingSelection(null);
      return;
    }

    const text = selection.toString().trim();
    if (!text) {
      setPendingSelection(null);
      return;
    }

    const preRange = document.createRange();
    preRange.selectNodeContents(containerRef.current);
    preRange.setEnd(range.startContainer, range.startOffset);
    const startOffset = preRange.toString().length;

    const rect = range.getBoundingClientRect();

    setPendingSelection({
      text,
      startOffset,
      endOffset: startOffset + text.length,
      rect,
    });
  }, []);

  const addComment = useCallback(
    (commentText: string) => {
      if (!pendingSelection) return;

      const newComment: ReviewComment = {
        id: crypto.randomUUID(),
        selectedText: pendingSelection.text,
        startOffset: pendingSelection.startOffset,
        endOffset: pendingSelection.endOffset,
        comment: commentText,
        timestamp: new Date().toISOString(),
        documentId,
      };

      setComments((prev) =>
        [...prev, newComment].sort((a, b) => a.startOffset - b.startOffset),
      );
      setPendingSelection(null);
      window.getSelection()?.removeAllRanges();
    },
    [pendingSelection, documentId],
  );

  const removeComment = useCallback((id: string) => {
    setComments((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const updateComment = useCallback((id: string, newText: string) => {
    setComments((prev) =>
      prev.map((c) => (c.id === id ? { ...c, comment: newText } : c)),
    );
  }, []);

  const clearPendingSelection = useCallback(() => {
    setPendingSelection(null);
    window.getSelection()?.removeAllRanges();
  }, []);

  return {
    comments,
    pendingSelection,
    containerRef,
    handleMouseUp,
    addComment,
    removeComment,
    updateComment,
    clearPendingSelection,
  };
}
