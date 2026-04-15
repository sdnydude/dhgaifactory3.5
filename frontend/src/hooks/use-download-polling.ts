"use client";

import { useEffect } from "react";
import { listJobs } from "@/lib/filesApi";
import { useDownloadsStore } from "@/stores/downloads-store";

export function useDownloadPolling(intervalMs = 3_000) {
  const jobs = useDownloadsStore((s) => s.jobs);
  const setJobs = useDownloadsStore((s) => s.setJobs);

  const hasActive = jobs.some(
    (j) => j.status === "pending" || j.status === "running",
  );

  useEffect(() => {
    if (!hasActive) return;

    let active = true;

    const poll = async () => {
      try {
        const fresh = await listJobs(20);
        if (!active) return;
        setJobs(fresh);
      } catch {
        // silently fail — tray will retry on next tick
      }
    };

    poll();
    const interval = window.setInterval(poll, intervalMs);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [hasActive, intervalMs, setJobs]);
}
