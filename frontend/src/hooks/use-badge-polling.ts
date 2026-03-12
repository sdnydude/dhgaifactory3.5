"use client";

import { useEffect } from "react";
import { useAppStore } from "@/stores/app-store";

export function useBadgePolling(intervalMs = 30_000) {
  const setBadgeCounts = useAppStore((s) => s.setBadgeCounts);

  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        const [inboxRes, projectsRes] = await Promise.all([
          fetch("/api/langgraph/threads/search", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ status: "interrupted", limit: 0 }),
          }),
          fetch(
            `${process.env.NEXT_PUBLIC_REGISTRY_API_URL || "http://localhost:8011"}/api/cme/projects?status=processing`,
          ),
        ]);

        if (!active) return;

        let inboxCount = 0;
        if (inboxRes.ok) {
          const data = await inboxRes.json();
          inboxCount = Array.isArray(data) ? data.length : 0;
        }

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
