"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { AGENT_CATALOG, getCatalogEntry } from "@/lib/agent-catalog";
import type { AgentCategory, AgentCatalogEntry } from "@/lib/agent-catalog";
import { getGraphStats } from "@/lib/agentsApi";
import type { GraphStats } from "@/lib/agentsApi";
import { AgentsLibraryToolbar } from "./agents-library-toolbar";
import type { ViewMode, SortField } from "./agents-library-toolbar";
import { AgentsLibraryGrid } from "./agents-library-grid";
import { AgentsLibraryList } from "./agents-library-list";
import { AgentsLibraryTable } from "./agents-library-table";
import { AgentSlideOver } from "./agent-slide-over";

/** Merged catalog entry + live stats — the display type for all views. */
export interface AgentLibraryItem extends AgentCatalogEntry {
  totalRuns: number;
  succeeded: number;
  failed: number;
  running: number;
  successRate: number;
  lastRunAt: string | null;
}

function mergeStats(catalog: AgentCatalogEntry[], stats: GraphStats[]): AgentLibraryItem[] {
  const statsMap = new Map(stats.map((s) => [s.graphId, s]));
  return catalog.map((entry) => {
    const s = statsMap.get(entry.graphId);
    return {
      ...entry,
      totalRuns: s?.totalRuns ?? 0,
      succeeded: s?.succeeded ?? 0,
      failed: s?.failed ?? 0,
      running: s?.running ?? 0,
      successRate: s?.successRate ?? 0,
      lastRunAt: s?.lastRunAt ?? null,
    };
  });
}

function sortItems(items: AgentLibraryItem[], field: SortField): AgentLibraryItem[] {
  const sorted = [...items];
  sorted.sort((a, b) => {
    switch (field) {
      case "name":
        return a.name.localeCompare(b.name);
      case "category":
        return a.category.localeCompare(b.category) || a.pipelineOrder - b.pipelineOrder;
      case "pipelineOrder":
        return a.pipelineOrder - b.pipelineOrder;
      case "successRate":
        return b.successRate - a.successRate;
      case "totalRuns":
        return b.totalRuns - a.totalRuns;
      default:
        return 0;
    }
  });
  return sorted;
}

export function AgentsLibrary() {
  const [view, setView] = useState<ViewMode>("grid");
  const [category, setCategory] = useState<AgentCategory | "all">("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortField>("pipelineOrder");
  const [selectedAgent, setSelectedAgent] = useState<AgentLibraryItem | null>(null);
  const [graphStats, setGraphStats] = useState<GraphStats[]>([]);

  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const fetchStats = useCallback(async () => {
    try {
      const stats = await getGraphStats();
      setGraphStats(stats);
    } catch (e) {
      console.error("Failed to fetch graph stats:", e);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    intervalRef.current = setInterval(fetchStats, 30_000);
    return () => clearInterval(intervalRef.current);
  }, [fetchStats]);

  // Merge catalog with stats
  const allItems = useMemo(() => mergeStats(AGENT_CATALOG, graphStats), [graphStats]);

  // Filter
  const filtered = useMemo(() => {
    let result = allItems;
    if (category !== "all") {
      result = result.filter((item) => item.category === category);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (item) =>
          item.name.toLowerCase().includes(q) ||
          item.description.toLowerCase().includes(q) ||
          item.graphId.toLowerCase().includes(q)
      );
    }
    return result;
  }, [allItems, category, search]);

  // Sort
  const sorted = useMemo(() => sortItems(filtered, sort), [filtered, sort]);

  // Category counts (from allItems, not filtered)
  const categoryCounts = useMemo(() => {
    const counts: Record<AgentCategory | "all", number> = {
      all: allItems.length,
      content: 0,
      recipe: 0,
      qa: 0,
      infra: 0,
    };
    for (const item of allItems) {
      counts[item.category]++;
    }
    return counts;
  }, [allItems]);

  const handleNavigate = useCallback(
    (graphId: string) => {
      const item = allItems.find((i) => i.graphId === graphId);
      if (item) setSelectedAgent(item);
    },
    [allItems]
  );

  return (
    <>
      {/* CSS keyframes injected via style tag */}
      <style>{`
        @keyframes agents-card-enter {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .agents-library-card-enter {
          animation: agents-card-enter 350ms ease-out both;
        }
      `}</style>

      <div
        className="p-4 space-y-4 overflow-auto h-full"
        style={{
          background: "radial-gradient(ellipse at top, var(--dhg-surface, hsl(var(--card))) 0%, transparent 70%)",
        }}
      >
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-semibold">Agents Library ({allItems.length})</h3>
        </div>

        <AgentsLibraryToolbar
          view={view}
          onViewChange={setView}
          category={category}
          onCategoryChange={setCategory}
          search={search}
          onSearchChange={setSearch}
          sort={sort}
          onSortChange={setSort}
          categoryCounts={categoryCounts}
        />

        {sorted.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            No agents match your filters.
          </div>
        ) : view === "grid" ? (
          <AgentsLibraryGrid items={sorted} onSelect={setSelectedAgent} />
        ) : view === "list" ? (
          <AgentsLibraryList items={sorted} onSelect={setSelectedAgent} />
        ) : (
          <AgentsLibraryTable items={sorted} onSelect={setSelectedAgent} sort={sort} onSortChange={setSort} />
        )}
      </div>

      <AgentSlideOver
        agent={selectedAgent}
        onClose={() => setSelectedAgent(null)}
        onNavigate={handleNavigate}
      />
    </>
  );
}
