"use client";

import * as React from "react";
import { listDevChangelog, type DevChangelogEntry } from "@/lib/devChangelogApi";
import { useDevChangelogStore } from "@/stores/dev-changelog-store";
import { DevChangelogTable } from "./dev-changelog-table";
import { DevChangelogDetailSheet } from "./dev-changelog-detail-sheet";
import { DevChangelogFilterRail } from "./dev-changelog-filter-rail";

export function DevChangelogView() {
  const entries = useDevChangelogStore((s) => s.entries);
  const total = useDevChangelogStore((s) => s.total);
  const loading = useDevChangelogStore((s) => s.loading);
  const error = useDevChangelogStore((s) => s.error);
  const filters = useDevChangelogStore((s) => s.filters);
  const setEntries = useDevChangelogStore((s) => s.setEntries);
  const setLoading = useDevChangelogStore((s) => s.setLoading);
  const setError = useDevChangelogStore((s) => s.setError);
  const selectRow = useDevChangelogStore((s) => s.selectRow);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listDevChangelog({ ...filters, limit: 500 })
      .then((result) => {
        if (cancelled) return;
        setEntries(result.entries, result.total);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load changelog");
      });
    return () => {
      cancelled = true;
    };
  }, [filters, setEntries, setLoading, setError]);

  const counts = React.useMemo(() => {
    const c = { shipped: 0, in_progress: 0, backlog: 0 };
    for (const e of entries) {
      const s = e.declared_status ?? e.detected_status;
      if (s === "shipped") c.shipped += 1;
      else if (s === "in_progress") c.in_progress += 1;
      else if (s === "backlog") c.backlog += 1;
    }
    return c;
  }, [entries]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">Development Changelog</h1>
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">
          {loading
            ? "Loading…"
            : error
              ? "Error"
              : `${total} entries · ${counts.shipped} shipped · ${counts.in_progress} in progress · ${counts.backlog} backlog`}
        </span>
      </div>

      {error && (
        <div className="mx-6 mt-3 flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-2.5">
          <span className="text-sm text-destructive">{error}</span>
        </div>
      )}

      <div className="flex flex-1 gap-0 overflow-hidden">
        <DevChangelogFilterRail />

        <main className="min-w-0 flex-1 overflow-auto px-6 py-5">
          {loading ? (
            <div className="text-sm text-muted-foreground">
              Loading changelog…
            </div>
          ) : (
            <DevChangelogTable
              entries={entries}
              onRowClick={(row: DevChangelogEntry) => selectRow(row.slug)}
            />
          )}
        </main>
      </div>

      <DevChangelogDetailSheet />
    </div>
  );
}
