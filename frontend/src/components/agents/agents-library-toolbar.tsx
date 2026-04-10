"use client";

import { LayoutGrid, List, Table2, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AgentCategory } from "@/lib/agent-catalog";

export type ViewMode = "grid" | "list" | "table";
export type SortField = "name" | "category" | "pipelineOrder" | "successRate" | "totalRuns";

const CATEGORIES: { value: AgentCategory | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "content", label: "Content" },
  { value: "recipe", label: "Recipes" },
  { value: "qa", label: "QA" },
  { value: "infra", label: "Infra" },
];

const CATEGORY_STYLES: Record<string, string> = {
  all: "border-zinc-300 dark:border-zinc-600",
  content: "border-[#663399] bg-[#663399]/10 text-[#663399] dark:text-[#a78bfa]",
  recipe: "border-[#F77E2D] bg-[#F77E2D]/10 text-[#F77E2D] dark:text-[#fb923c]",
  qa: "border-[#22c55e] bg-[#22c55e]/10 text-[#16a34a] dark:text-[#4ade80]",
  infra: "border-zinc-500 bg-zinc-500/10 text-zinc-500 dark:text-zinc-400",
};

interface ToolbarProps {
  view: ViewMode;
  onViewChange: (v: ViewMode) => void;
  category: AgentCategory | "all";
  onCategoryChange: (c: AgentCategory | "all") => void;
  search: string;
  onSearchChange: (s: string) => void;
  sort: SortField;
  onSortChange: (s: SortField) => void;
  categoryCounts: Record<AgentCategory | "all", number>;
}

export function AgentsLibraryToolbar({
  view,
  onViewChange,
  category,
  onCategoryChange,
  search,
  onSearchChange,
  sort,
  onSortChange,
  categoryCounts,
}: ToolbarProps) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Category filter pills */}
      <div className="flex items-center gap-1.5">
        {CATEGORIES.map((cat) => (
          <Badge
            key={cat.value}
            variant="outline"
            className={`cursor-pointer text-[11px] px-2.5 py-0.5 transition-colors ${
              category === cat.value
                ? CATEGORY_STYLES[cat.value]
                : "border-border text-muted-foreground hover:border-foreground/30"
            }`}
            onClick={() => onCategoryChange(cat.value)}
          >
            {cat.label} ({categoryCounts[cat.value]})
          </Badge>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Search */}
      <div className="relative w-52">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          placeholder="Search agents..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-8 h-8 text-xs"
        />
      </div>

      {/* Sort */}
      <Select value={sort} onValueChange={(v) => onSortChange(v as SortField)}>
        <SelectTrigger className="w-36 h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="pipelineOrder">Pipeline Order</SelectItem>
          <SelectItem value="name">Name</SelectItem>
          <SelectItem value="category">Category</SelectItem>
          <SelectItem value="successRate">Success Rate</SelectItem>
          <SelectItem value="totalRuns">Total Runs</SelectItem>
        </SelectContent>
      </Select>

      {/* View toggle */}
      <div className="flex items-center border border-border rounded-md">
        <Button
          variant={view === "grid" ? "secondary" : "ghost"}
          size="sm"
          className="h-8 w-8 p-0 rounded-r-none"
          onClick={() => onViewChange("grid")}
        >
          <LayoutGrid className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant={view === "list" ? "secondary" : "ghost"}
          size="sm"
          className="h-8 w-8 p-0 rounded-none border-x border-border"
          onClick={() => onViewChange("list")}
        >
          <List className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant={view === "table" ? "secondary" : "ghost"}
          size="sm"
          className="h-8 w-8 p-0 rounded-l-none"
          onClick={() => onViewChange("table")}
        >
          <Table2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
