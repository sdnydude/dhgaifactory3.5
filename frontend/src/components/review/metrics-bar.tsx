"use client";

import { Badge } from "@/components/ui/badge";
import type { ReviewMetrics } from "./types";

interface MetricsBarProps {
  metrics: ReviewMetrics;
  reviewRound: number;
}

export function MetricsBar({ metrics, reviewRound }: MetricsBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 px-4 py-2 border-b border-border bg-muted/50">
      {metrics.word_count != null && (
        <Badge variant="outline" className="text-xs">
          {metrics.word_count.toLocaleString()} words
        </Badge>
      )}
      {metrics.prose_density != null && (
        <Badge variant="outline" className="text-xs">
          {(metrics.prose_density * 100).toFixed(0)}% prose density
        </Badge>
      )}
      {metrics.quality_passed != null && (
        <Badge
          variant={metrics.quality_passed ? "default" : "destructive"}
          className="text-xs"
        >
          QA {metrics.quality_passed ? "Passed" : "Failed"}
        </Badge>
      )}
      {metrics.banned_patterns_found && metrics.banned_patterns_found.length > 0 && (
        <Badge variant="destructive" className="text-xs">
          {metrics.banned_patterns_found.length} banned patterns
        </Badge>
      )}
      {reviewRound > 0 && (
        <Badge variant="secondary" className="text-xs">
          Revision {reviewRound}/3
        </Badge>
      )}
    </div>
  );
}
