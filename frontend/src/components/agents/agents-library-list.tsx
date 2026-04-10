"use client";

import { ChevronRight } from "lucide-react";
import type { AgentCategory } from "@/lib/agent-catalog";
import { CATEGORY_META } from "@/lib/agent-catalog";
import type { AgentLibraryItem } from "./agents-library";

const CATEGORY_DOT: Record<AgentCategory, string> = {
  content: "bg-[#663399]",
  recipe: "bg-[#F77E2D]",
  qa: "bg-[#22c55e]",
  infra: "bg-zinc-500",
};

interface ListViewProps {
  items: AgentLibraryItem[];
  onSelect: (item: AgentLibraryItem) => void;
}

export function AgentsLibraryList({ items, onSelect }: ListViewProps) {
  const groups = new Map<AgentCategory, AgentLibraryItem[]>();
  for (const item of items) {
    const list = groups.get(item.category) ?? [];
    list.push(item);
    groups.set(item.category, list);
  }
  const sortedGroups = [...groups.entries()].sort(
    (a, b) => CATEGORY_META[a[0]].order - CATEGORY_META[b[0]].order
  );

  return (
    <div className="space-y-4">
      {sortedGroups.map(([cat, catItems]) => (
        <div key={cat}>
          <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            {CATEGORY_META[cat].label}
          </h4>
          <div className="space-y-0.5">
            {catItems.map((item) => (
              <button
                key={item.graphId}
                onClick={() => onSelect(item)}
                className="w-full text-left grid grid-cols-[24px_1fr_80px_60px_60px_20px] items-center gap-2 px-3 py-2 rounded-md hover:bg-muted/50 transition-colors group"
              >
                {/* Icon */}
                <span className="text-sm">{item.icon}</span>

                {/* Name + description */}
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium truncate">{item.name}</span>
                    <span className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${CATEGORY_DOT[item.category]}`} />
                  </div>
                  <p className="text-[10px] text-muted-foreground truncate">{item.description}</p>
                </div>

                {/* Success bar */}
                <div className="flex items-center gap-1.5">
                  <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-green-500"
                      style={{ width: `${item.successRate}%` }}
                    />
                  </div>
                  <span className="text-[10px] tabular-nums w-7 text-right">{item.successRate}%</span>
                </div>

                {/* Total runs */}
                <span className="text-[10px] text-muted-foreground text-right tabular-nums">
                  {item.totalRuns} runs
                </span>

                {/* Running */}
                <span className="text-[10px] text-muted-foreground text-right tabular-nums">
                  {item.running > 0 ? `${item.running} active` : ""}
                </span>

                {/* Chevron */}
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
