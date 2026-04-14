"use client";

import * as React from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useDevChangelogStore } from "@/stores/dev-changelog-store";
import type {
  DevChangelogCategory,
  DevChangelogEntry,
  DevChangelogStatus,
} from "@/lib/devChangelogApi";

const STATUS_OPTIONS: Array<{ value: DevChangelogStatus; label: string }> = [
  { value: "shipped", label: "Shipped" },
  { value: "in_progress", label: "In progress" },
  { value: "backlog", label: "Backlog" },
  { value: "abandoned", label: "Abandoned" },
];

const CATEGORY_OPTIONS: Array<{ value: DevChangelogCategory; label: string }> = [
  { value: "feature", label: "Feature" },
  { value: "infra", label: "Infra" },
  { value: "fix", label: "Fix" },
  { value: "refactor", label: "Refactor" },
  { value: "docs", label: "Docs" },
  { value: "debt", label: "Debt" },
];

function displayStatus(entry: DevChangelogEntry): DevChangelogStatus {
  return entry.declared_status ?? entry.detected_status;
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
      {children}
    </h3>
  );
}

function FacetChip({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex w-full items-center justify-between gap-2 rounded-md border px-2.5 py-1.5 text-left text-[11px] transition-colors",
        active
          ? "border-primary/40 bg-primary/10 text-foreground"
          : "border-border bg-background hover:bg-muted/60 text-muted-foreground hover:text-foreground",
      )}
    >
      <span>{label}</span>
      <span
        className={cn(
          "font-mono tabular-nums text-[10px]",
          active ? "text-foreground/70" : "text-muted-foreground/70",
        )}
      >
        {count}
      </span>
    </button>
  );
}

export function DevChangelogFilterRail() {
  const filters = useDevChangelogStore((s) => s.filters);
  const setFilter = useDevChangelogStore((s) => s.setFilter);
  const clearFilters = useDevChangelogStore((s) => s.clearFilters);
  const entries = useDevChangelogStore((s) => s.entries);

  const [searchDraft, setSearchDraft] = React.useState<string>(filters.q ?? "");

  // Sync draft when filters.q changes from elsewhere (e.g. Clear all).
  React.useEffect(() => {
    setSearchDraft(filters.q ?? "");
  }, [filters.q]);

  // Debounced push of searchDraft into filters.q.
  React.useEffect(() => {
    const trimmed = searchDraft.trim();
    if (trimmed === (filters.q ?? "")) return;
    const id = setTimeout(() => {
      setFilter("q", trimmed === "" ? undefined : trimmed);
    }, 300);
    return () => clearTimeout(id);
  }, [searchDraft, filters.q, setFilter]);

  const counts = React.useMemo(() => {
    const status: Record<DevChangelogStatus, number> = {
      shipped: 0,
      in_progress: 0,
      backlog: 0,
      abandoned: 0,
    };
    const category: Record<DevChangelogCategory, number> = {
      feature: 0,
      infra: 0,
      fix: 0,
      refactor: 0,
      docs: 0,
      debt: 0,
    };
    for (const entry of entries) {
      status[displayStatus(entry)] += 1;
      category[entry.category] += 1;
    }
    return { status, category };
  }, [entries]);

  const hasAnyFilter =
    !!filters.status ||
    !!filters.category ||
    !!filters.window_start ||
    !!filters.window_end ||
    !!filters.q;

  return (
    <aside
      aria-label="Dev changelog filters"
      className="hidden w-[260px] shrink-0 flex-col gap-5 border-r px-5 py-5 lg:flex"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Filters
        </h2>
        {hasAnyFilter && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="h-6 px-2 text-[10px]"
          >
            <X className="h-3 w-3" />
            Clear
          </Button>
        )}
      </div>

      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          value={searchDraft}
          onChange={(e) => setSearchDraft(e.target.value)}
          placeholder="Search notes, insight, epic…"
          className="h-8 pl-8 text-[12px]"
        />
      </div>

      <section className="space-y-2">
        <SectionHeader>Status</SectionHeader>
        <div className="flex flex-col gap-1.5">
          {STATUS_OPTIONS.map((opt) => {
            const active = filters.status === opt.value;
            return (
              <FacetChip
                key={opt.value}
                label={opt.label}
                count={counts.status[opt.value]}
                active={active}
                onClick={() =>
                  setFilter("status", active ? undefined : opt.value)
                }
              />
            );
          })}
        </div>
      </section>

      <section className="space-y-2">
        <SectionHeader>Category</SectionHeader>
        <div className="flex flex-col gap-1.5">
          {CATEGORY_OPTIONS.map((opt) => {
            const active = filters.category === opt.value;
            return (
              <FacetChip
                key={opt.value}
                label={opt.label}
                count={counts.category[opt.value]}
                active={active}
                onClick={() =>
                  setFilter("category", active ? undefined : opt.value)
                }
              />
            );
          })}
        </div>
      </section>

      <section className="space-y-2">
        <SectionHeader>Window</SectionHeader>
        <div className="space-y-2">
          <label className="block space-y-1">
            <span className="text-[10px] text-muted-foreground">From</span>
            <Input
              type="date"
              value={filters.window_start ?? ""}
              onChange={(e) =>
                setFilter("window_start", e.target.value || undefined)
              }
              className="h-8 text-[11px]"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[10px] text-muted-foreground">To</span>
            <Input
              type="date"
              value={filters.window_end ?? ""}
              onChange={(e) =>
                setFilter("window_end", e.target.value || undefined)
              }
              className="h-8 text-[11px]"
            />
          </label>
        </div>
      </section>
    </aside>
  );
}
