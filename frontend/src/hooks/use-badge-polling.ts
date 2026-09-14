"use client";

import { useEffect } from "react";
import { useAppStore } from "@/stores/app-store";
import { getMyReviews } from "@/lib/registryApi";

// Inlined by Next at build time. Without a reviewer identity there is no
// review queue to count, so the badge stays at 0 and no request is made.
const REVIEWER_EMAIL = process.env.NEXT_PUBLIC_REVIEWER_EMAIL ?? "";

export function useBadgePolling(intervalMs = 30_000) {
  const setBadgeCounts = useAppStore((s) => s.setBadgeCounts);

  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        // Inbox badge counts the reviewer's own registry review queue.
        // "active" assignments are the ones awaiting this reviewer now.
        const [inboxCount, projectsRes] = await Promise.all([
          REVIEWER_EMAIL
            ? getMyReviews(REVIEWER_EMAIL).then((r) => r.count).catch(() => 0)
            : Promise.resolve(0),
          fetch("/api/registry/api/cme/projects?status=processing"),
        ]);

        if (!active) return;

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
