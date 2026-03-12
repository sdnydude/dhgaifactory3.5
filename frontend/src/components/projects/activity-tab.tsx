"use client";

import { Activity } from "lucide-react";
import type { ExecutionStatus } from "@/types/cme";

export function ActivityTab({ status }: { status: ExecutionStatus | null }) {
  if (!status) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Activity className="h-10 w-10 text-muted-foreground/50 mb-3" />
        <p className="text-sm text-muted-foreground">No activity yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {status.agents_completed.map((agent) => (
        <div key={agent} className="flex items-center gap-3 text-xs border-b border-border py-2">
          <span className="h-2 w-2 rounded-full bg-green-500 shrink-0" />
          <span className="font-medium">{agent}</span>
          <span className="text-muted-foreground">completed</span>
        </div>
      ))}
      {status.current_agent && (
        <div className="flex items-center gap-3 text-xs border-b border-border py-2">
          <span className="h-2 w-2 rounded-full bg-dhg-orange animate-pulse shrink-0" />
          <span className="font-medium">{status.current_agent}</span>
          <span className="text-muted-foreground">running</span>
        </div>
      )}
      {status.agents_pending.map((agent) => (
        <div key={agent} className="flex items-center gap-3 text-xs border-b border-border py-2">
          <span className="h-2 w-2 rounded-full bg-muted-foreground/30 shrink-0" />
          <span className="text-muted-foreground">{agent}</span>
          <span className="text-muted-foreground">pending</span>
        </div>
      ))}
      {status.errors.length > 0 && (
        <div className="mt-4 space-y-1">
          <h4 className="text-xs font-semibold text-destructive">Errors</h4>
          {status.errors.map((err, i) => (
            <p key={i} className="text-xs text-destructive/80">
              {JSON.stringify(err)}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
