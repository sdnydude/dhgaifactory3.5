"use client";

import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AgentCategory } from "@/lib/agent-catalog";
import type { AgentLibraryItem } from "./agents-library";
import type { SortField } from "./agents-library-toolbar";

const CATEGORY_BADGE: Record<AgentCategory, string> = {
  content: "bg-[#663399]/10 text-[#663399] dark:text-[#a78bfa]",
  recipe: "bg-[#F77E2D]/10 text-[#F77E2D] dark:text-[#fb923c]",
  qa: "bg-[#22c55e]/10 text-[#16a34a] dark:text-[#4ade80]",
  infra: "bg-zinc-500/10 text-zinc-500 dark:text-zinc-400",
};

interface TableViewProps {
  items: AgentLibraryItem[];
  onSelect: (item: AgentLibraryItem) => void;
  sort: SortField;
  onSortChange: (s: SortField) => void;
}

function SortHeader({
  label,
  field,
  currentSort,
  onSort,
  align,
}: {
  label: string;
  field: SortField;
  currentSort: SortField;
  onSort: (s: SortField) => void;
  align?: "left" | "right";
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className={`h-7 text-[10px] font-semibold uppercase tracking-wider px-1 ${
        align === "right" ? "justify-end" : ""
      } ${currentSort === field ? "text-foreground" : "text-muted-foreground"}`}
      onClick={() => onSort(field)}
    >
      {label}
      <ArrowUpDown className="ml-1 h-3 w-3" />
    </Button>
  );
}

export function AgentsLibraryTable({ items, onSelect, sort, onSortChange }: TableViewProps) {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="overflow-auto max-h-[calc(100vh-220px)]">
        <table className="w-full text-xs">
          <thead className="sticky top-0 z-10 bg-muted/80 backdrop-blur-sm border-b border-border">
            <tr>
              <th className="text-left px-3 py-2 w-8" />
              <th className="text-left px-1 py-2">
                <SortHeader label="Agent" field="name" currentSort={sort} onSort={onSortChange} />
              </th>
              <th className="text-left px-1 py-2 w-24">
                <SortHeader label="Category" field="category" currentSort={sort} onSort={onSortChange} />
              </th>
              <th className="text-right px-1 py-2 w-16">
                <SortHeader label="Order" field="pipelineOrder" currentSort={sort} onSort={onSortChange} align="right" />
              </th>
              <th className="text-right px-1 py-2 w-20">
                <SortHeader label="Runs" field="totalRuns" currentSort={sort} onSort={onSortChange} align="right" />
              </th>
              <th className="text-right px-1 py-2 w-28">
                <SortHeader label="Success" field="successRate" currentSort={sort} onSort={onSortChange} align="right" />
              </th>
              <th className="text-right px-3 py-2 w-20">
                <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Active</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr
                key={item.graphId}
                onClick={() => onSelect(item)}
                className={`cursor-pointer border-b border-border/50 transition-colors hover:bg-muted/40 ${
                  idx % 2 === 1 ? "bg-muted/20" : ""
                }`}
              >
                <td className="px-3 py-2 text-center">
                  <span className="text-sm">{item.icon}</span>
                </td>
                <td className="px-1 py-2">
                  <div>
                    <span className="font-medium">{item.name}</span>
                    <p className="text-[10px] text-muted-foreground truncate max-w-xs">{item.description}</p>
                  </div>
                </td>
                <td className="px-1 py-2">
                  <span className={`inline-block text-[10px] px-2 py-0.5 rounded-full ${CATEGORY_BADGE[item.category]}`}>
                    {item.category}
                  </span>
                </td>
                <td className="px-1 py-2 text-right tabular-nums text-muted-foreground">
                  {item.pipelineOrder > 0 ? item.pipelineOrder : "\u2014"}
                </td>
                <td className="px-1 py-2 text-right tabular-nums">
                  {item.totalRuns}
                </td>
                <td className="px-1 py-2">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-green-500 transition-all duration-500"
                        style={{ width: `${item.successRate}%` }}
                      />
                    </div>
                    <span className="tabular-nums w-8 text-right">{item.successRate}%</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {item.running > 0 && (
                    <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                      {item.running}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
