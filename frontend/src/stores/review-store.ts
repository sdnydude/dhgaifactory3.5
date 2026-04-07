"use client";

import { create } from "zustand";
import type { PendingReview } from "@/lib/inboxApi";

interface ReviewState {
  reviews: PendingReview[];
  selectedReviewId: string | null;
  loading: boolean;
  error: string | null;
  actionLoading: string | null;

  setReviews: (reviews: PendingReview[]) => void;
  selectReview: (threadId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setActionLoading: (threadId: string | null) => void;
  removeReview: (threadId: string) => void;
}

export const useReviewStore = create<ReviewState>()((set) => ({
  reviews: [],
  selectedReviewId: null,
  loading: true,
  error: null,
  actionLoading: null,

  setReviews: (reviews) => set({ reviews, loading: false }),
  selectReview: (threadId) => set({ selectedReviewId: threadId }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, loading: false }),
  setActionLoading: (threadId) => set({ actionLoading: threadId }),
  removeReview: (threadId) =>
    set((s) => ({
      reviews: s.reviews.filter((r) => r.threadId !== threadId),
      selectedReviewId:
        s.selectedReviewId === threadId ? null : s.selectedReviewId,
    })),
}));
