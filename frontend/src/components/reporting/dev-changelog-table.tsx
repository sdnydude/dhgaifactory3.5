"use client";

import * as React from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { cn } from "@/lib/utils";
import type {
  DevChangelogEntry,
  DevChangelogCategory,
  DevChangelogStatus,
} from "@/lib/devChangelogApi";

interface DevChangelogTableProps {
  entries: DevChangelogEntry[];
  onRowClick?: (entry: DevChangelogEntry) => void;
}

const CATEGORY_TONE: Record<DevChangelogCategory, string> = {
  feature: "border-emerald-500/40 text-emerald-700 dark:text-emerald-300",
  infra: "border-sky-500/40 text-sky-700 dark:text-sky-300",
  fix: "border-amber-500/40 text-amber-700 dark:text-amber-300",
  refactor: "border-violet-500/40 text-violet-700 dark:text-violet-300",
  docs: "border-zinc-500/40 text-zinc-600 dark:text-zinc-300",
  debt: "border-rose-500/40 text-rose-700 dark:text-rose-300",
};

const STATUS_TONE: Record<DevChangelogStatus, string> = {
  shipped: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 ring-emerald-500/30",
  in_progress: "bg-amber-500/15 text-amber-700 dark:text-amber-300 ring-amber-500/30",
  backlog: "bg-zinc-500/15 text-zinc-700 dark:text-zinc-300 ring-zinc-500/30",
  abandoned: "bg-rose-500/15 text-rose-600 dark:text-rose-300 ring-rose-500/30",
};

const STATUS_LABEL: Record<DevChangelogStatus, string> = {
  shipped: "Shipped",
  in_progress: "In progress",
  backlog: "Backlog",
  abandoned: "Abandoned",
};

function displayStatus(entry: DevChangelogEntry): DevChangelogStatus {
  return entry.declared_status ?? entry.detected_status;
}

function formatShortDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "2-digit",
  });
}

const readOnlyCell = "bg-muted/20";

const columns: ColumnDef<DevChangelogEntry>[] = [
  {
    accessorKey: "slug",
    header: "Slug",
    cell: ({ row }) => (
      <span className="font-mono text-[11px] text-foreground/80">
        {row.original.slug}
      </span>
    ),
  },
  {
    accessorKey: "epic",
    header: "Epic",
    cell: ({ row }) => (
      <span className="font-serif-body text-[14px] leading-snug text-foreground">
        {row.original.epic}
      </span>
    ),
  },
  {
    accessorKey: "category",
    header: "Cat",
    cell: ({ row }) => {
      const cat = row.original.category;
      return (
        <span
          className={cn(
            "inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.12em]",
            CATEGORY_TONE[cat],
          )}
        >
          {cat}
        </span>
      );
    },
  },
  {
    accessorKey: "window_start",
    header: "Start",
    cell: ({ row }) => (
      <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
        {formatShortDate(row.original.window_start)}
      </span>
    ),
  },
  {
    accessorKey: "commit_count",
    header: "Commits",
    cell: ({ row }) => (
      <span className="font-mono text-[11px] tabular-nums text-foreground/80">
        {row.original.commit_count}
      </span>
    ),
  },
  {
    id: "display_status",
    header: "Status",
    accessorFn: (row) => displayStatus(row),
    cell: ({ row }) => {
      const s = displayStatus(row.original);
      return (
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em] ring-1 ring-inset",
            STATUS_TONE[s],
          )}
        >
          {STATUS_LABEL[s]}
        </span>
      );
    },
    sortingFn: (a, b) => {
      const order: Record<DevChangelogStatus, number> = {
        shipped: 0,
        in_progress: 1,
        backlog: 2,
        abandoned: 3,
      };
      return order[displayStatus(a.original)] - order[displayStatus(b.original)];
    },
  },
  {
    accessorKey: "declared_status",
    header: "Override",
    cell: ({ row }) => {
      const v = row.original.declared_status;
      return (
        <span
          className={cn(
            "inline-block rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground",
            readOnlyCell,
          )}
        >
          {v ? STATUS_LABEL[v] : "—"}
        </span>
      );
    },
  },
  {
    accessorKey: "priority",
    header: "Pri",
    cell: ({ row }) => (
      <span
        className={cn(
          "inline-block rounded px-1.5 py-0.5 font-mono text-[11px] tabular-nums text-muted-foreground",
          readOnlyCell,
        )}
      >
        {row.original.priority ?? "—"}
      </span>
    ),
  },
  {
    accessorKey: "locked",
    header: "Lock",
    cell: ({ row }) => (
      <span
        className={cn(
          "inline-block rounded px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground",
          readOnlyCell,
        )}
        aria-label={row.original.locked ? "locked" : "unlocked"}
      >
        {row.original.locked ? "🔒" : "·"}
      </span>
    ),
  },
];

export function DevChangelogTable({
  entries,
  onRowClick,
}: DevChangelogTableProps) {
  return (
    <DataTable<DevChangelogEntry, unknown>
      columns={columns}
      data={entries}
      initialSorting={[{ id: "window_start", desc: true }]}
      onRowClick={onRowClick}
      emptyMessage="No changelog entries match the current filters."
      className="border-t border-border"
      enableSearch={false}
      pageSize={25}
    />
  );
}
