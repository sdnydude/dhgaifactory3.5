"use client";

import { Badge } from "@/components/ui/badge";
import type { AgentCategory } from "@/lib/agent-catalog";
import { CATEGORY_META } from "@/lib/agent-catalog";
import type { AgentLibraryItem } from "./agents-library";

const CATEGORY_BORDER: Record<AgentCategory, string> = {
  content: "border-t-[#663399]",
  recipe: "border-t-[#F77E2D]",
  qa: "border-t-[#22c55e]",
  infra: "border-t-zinc-500",
};

const CATEGORY_SHADOW: Record<AgentCategory, string> = {
  content: "hover:shadow-[0_4px_12px_rgba(102,51,153,0.15)] dark:hover:shadow-[0_4px_12px_rgba(167,139,250,0.15)]",
  recipe: "hover:shadow-[0_4px_12px_rgba(247,126,45,0.15)] dark:hover:shadow-[0_4px_12px_rgba(251,146,60,0.15)]",
  qa: "hover:shadow-[0_4px_12px_rgba(34,197,94,0.15)] dark:hover:shadow-[0_4px_12px_rgba(74,222,128,0.15)]",
  infra: "hover:shadow-[0_4px_12px_rgba(113,113,122,0.15)] dark:hover:shadow-[0_4px_12px_rgba(161,161,170,0.15)]",
};

function healthBorder(lastRunAt: string | null): string {
  if (!lastRunAt) return "border-l-transparent";
  const hoursSince = (Date.now() - new Date(lastRunAt).getTime()) / (1000 * 60 * 60);
  if (hoursSince <= 24) return "border-l-green-500";
  return "border-l-amber-500";
}

interface GridViewProps {
  items: AgentLibraryItem[];
  onSelect: (item: AgentLibraryItem) => void;
}

export function AgentsLibraryGrid({ items, onSelect }: GridViewProps) {
  // Group by category, sorted by CATEGORY_META order
  const groups = new Map<AgentCategory, AgentLibraryItem[]>();
  for (const item of items) {
    const list = groups.get(item.category) ?? [];
    list.push(item);
    groups.set(item.category, list);
  }
  const sortedGroups = [...groups.entries()].sort(
    (a, b) => CATEGORY_META[a[0]].order - CATEGORY_META[b[0]].order
  );

  let globalIndex = 0;

  return (
    <div className="space-y-6">
      {sortedGroups.map(([cat, catItems]) => (
        <div key={cat}>
          <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            {CATEGORY_META[cat].label} ({catItems.length})
          </h4>
          <div className="grid grid-cols-3 gap-3">
            {catItems.map((item) => {
              const idx = globalIndex++;
              return (
                <button
                  key={item.graphId}
                  onClick={() => onSelect(item)}
                  className={`
                    text-left rounded-lg border border-border border-t-2 border-l-2
                    ${CATEGORY_BORDER[item.category]}
                    ${healthBorder(item.lastRunAt)}
                    ${CATEGORY_SHADOW[item.category]}
                    bg-card p-3 transition-all duration-200
                    hover:translate-y-[-1px]
                    agents-library-card-enter
                  `}
                  style={{ animationDelay: `${idx * 40}ms` }}
                >
                  <div className="flex items-start gap-2">
                    <span className="text-lg leading-none mt-0.5">{item.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-medium truncate">{item.name}</span>
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-0.5 leading-snug line-clamp-2">
                        {item.description}
                      </p>
                    </div>
                  </div>

                  {/* Stats row */}
                  <div className="flex items-center gap-2 mt-2.5 pt-2 border-t border-border/50">
                    <span className="text-[10px] text-muted-foreground">
                      {item.totalRuns} runs
                    </span>
                    {item.totalRuns > 0 && (
                      <>
                        <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-green-500 transition-all duration-500"
                            style={{ width: `${item.successRate}%` }}
                          />
                        </div>
                        <span className="text-[10px] font-medium tabular-nums">
                          {item.successRate}%
                        </span>
                      </>
                    )}
                    {item.totalRuns === 0 && (
                      <span className="text-[10px] text-muted-foreground italic">no data</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
