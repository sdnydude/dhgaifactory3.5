"use client";

import { useEffect, useState, useCallback } from "react";
import { InboxItem } from "./inbox-item";
import { listPendingReviews, resumeThread } from "@/lib/inboxApi";
import type { PendingReview } from "@/lib/inboxApi";
import type { ResumeValue } from "@/components/review/types";
import { Inbox, RefreshCw, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export function InboxList() {
  const [reviews, setReviews] = useState<PendingReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listPendingReviews();
      setReviews(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load pending reviews",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReviews();
    const interval = setInterval(fetchReviews, 30000);
    return () => clearInterval(interval);
  }, [fetchReviews]);

  const handleAction = async (
    threadId: string,
    graphId: string,
    resumeValue: ResumeValue,
  ) => {
    setActionLoading(threadId);
    try {
      await resumeThread(threadId, graphId, resumeValue);
      setReviews((prev) => prev.filter((r) => r.threadId !== threadId));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to process review action",
      );
    } finally {
      setActionLoading(null);
    }
  };

  if (loading && reviews.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <RefreshCw className="h-5 w-5 animate-spin mr-2" />
        Loading pending reviews...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-foreground">
            Pending Reviews
          </h2>
          <span className="text-sm text-muted-foreground">
            ({reviews.length})
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={fetchReviews}
          disabled={loading}
        >
          <RefreshCw
            className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {reviews.length === 0 && !error ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <Inbox className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-sm">No pending reviews</p>
          <p className="text-xs mt-1">
            Reviews appear here when CME pipeline agents reach human review
            gates.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {reviews.map((review) => (
            <InboxItem
              key={review.threadId}
              review={review}
              onAction={handleAction}
              isLoading={actionLoading === review.threadId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
