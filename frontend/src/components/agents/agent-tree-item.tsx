"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { RunningAgent } from "@/lib/agentsApi";

const STATUS_COLORS: Record<string, string> = {
  running: "bg-dhg-orange",
  success: "bg-green-500",
  error: "bg-destructive",
  pending: "bg-muted-foreground/30",
  interrupted: "bg-yellow-500",
};

interface AgentTreeItemProps {
  agent: RunningAgent;
  selected: boolean;
  onClick: () => void;
}

export function AgentTreeItem({ agent, selected, onClick }: AgentTreeItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 w-full text-left px-3 py-2 rounded-md text-xs transition-colors",
        selected ? "bg-primary/10 text-primary" : "text-foreground hover:bg-muted",
      )}
    >
      <span className={cn("h-2 w-2 rounded-full shrink-0", STATUS_COLORS[agent.status] ?? "bg-muted-foreground/30")} />
      <div className="flex-1 min-w-0">
        <span className="block truncate font-medium">{agent.graphId}</span>
        {agent.projectName && (
          <span className="block truncate text-[10px] text-muted-foreground">{agent.projectName}</span>
        )}
      </div>
      <Badge variant="outline" className="text-[9px] shrink-0">
        {agent.status}
      </Badge>
    </button>
  );
}
