"use client";

import { useEffect } from "react";
import { useAppStore } from "@/stores/app-store";
import { listPendingReviews } from "@/lib/inboxApi";

export function useBadgePolling(intervalMs = 30_000) {
  const setBadgeCounts = useAppStore((s) => s.setBadgeCounts);

  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        // Inbox badge reuses the same helper the /inbox page uses, so
        // the count cannot drift from the list. listPendingReviews
        // filters out zombie interrupted threads that have no real
        // review payload.
        const [inboxReviews, projectsRes] = await Promise.all([
          listPendingReviews().catch(() => []),
          fetch("/api/registry/api/cme/projects?status=processing"),
        ]);

        if (!active) return;

        const inboxCount = inboxReviews.length;

        let processingCount = 0;
        if (projectsRes.ok) {
          const data = await projectsRes.json();
          processingCount = Array.isArray(data) ? data.length : 0;
        }

        setBadgeCounts({ inbox: inboxCount, processing: processingCount });
      } catch {
        // silently fail — badge counts are non-critical
      }
    };

    poll();
    const interval = setInterval(poll, intervalMs);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [intervalMs, setBadgeCounts]);
}
