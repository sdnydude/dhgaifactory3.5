"use client";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useIncidentsStore } from "@/stores/incidents-store";

const STATUSES = ["active", "mitigated", "resolved", "postmortem"];
const SEVERITIES = ["critical", "high", "medium", "low"];
const CATEGORIES = [
  "infrastructure",
  "pipeline",
  "data",
  "integration",
  "security",
  "performance",
];

export function IncidentFilters() {
  const filterStatus = useIncidentsStore((s) => s.filterStatus);
  const filterSeverity = useIncidentsStore((s) => s.filterSeverity);
  const filterCategory = useIncidentsStore((s) => s.filterCategory);
  const setFilterStatus = useIncidentsStore((s) => s.setFilterStatus);
  const setFilterSeverity = useIncidentsStore((s) => s.setFilterSeverity);
  const setFilterCategory = useIncidentsStore((s) => s.setFilterCategory);
  const clearFilters = useIncidentsStore((s) => s.clearFilters);
  const fetchAll = useIncidentsStore((s) => s.fetchAll);

  const hasFilters = filterStatus || filterSeverity || filterCategory;

  function applyFilter(setter: (v: string | null) => void, value: string | null) {
    setter(!value || value === "all" ? null : value);
    setTimeout(fetchAll, 0);
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <Select
        value={filterStatus ?? "all"}
        onValueChange={(v) => applyFilter(setFilterStatus, v)}
      >
        <SelectTrigger className="h-8 w-[120px] text-xs">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Status</SelectItem>
          {STATUSES.map((s) => (
            <SelectItem key={s} value={s} className="capitalize">
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filterSeverity ?? "all"}
        onValueChange={(v) => applyFilter(setFilterSeverity, v)}
      >
        <SelectTrigger className="h-8 w-[120px] text-xs">
          <SelectValue placeholder="Severity" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Severity</SelectItem>
          {SEVERITIES.map((s) => (
            <SelectItem key={s} value={s} className="capitalize">
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filterCategory ?? "all"}
        onValueChange={(v) => applyFilter(setFilterCategory, v)}
      >
        <SelectTrigger className="h-8 w-[130px] text-xs">
          <SelectValue placeholder="Category" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Categories</SelectItem>
          {CATEGORIES.map((c) => (
            <SelectItem key={c} value={c} className="capitalize">
              {c}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {hasFilters && (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-xs"
          onClick={() => {
            clearFilters();
            setTimeout(fetchAll, 0);
          }}
        >
          Clear
        </Button>
      )}
    </div>
  );
}
