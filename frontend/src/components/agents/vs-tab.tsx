"use client";

import type { ThreadState } from "@/lib/agentsApi";

interface VsTabProps {
  state: ThreadState | null;
}

export function VsTab({ state }: VsTabProps) {
  return (
    <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
      VS tab
    </div>
  );
}
