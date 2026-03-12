"use client";

import { ClipboardCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { CMEProjectDetail } from "@/types/cme";

export function ReviewsTab({ project }: { project: CMEProjectDetail }) {
  if (!project.human_review_status) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <ClipboardCheck className="h-10 w-10 text-muted-foreground/50 mb-3" />
        <p className="text-sm text-muted-foreground">No reviews yet</p>
        <p className="text-xs text-muted-foreground">Reviews will appear when the pipeline reaches a review gate.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium">Review Status:</span>
        <Badge variant="outline">{project.human_review_status}</Badge>
      </div>
    </div>
  );
}
