"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type ProjectFilter = "all" | "active" | "review" | "complete";

interface ProjectFiltersProps {
  value: ProjectFilter;
  onChange: (value: ProjectFilter) => void;
}

export function ProjectFilters({ value, onChange }: ProjectFiltersProps) {
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as ProjectFilter)}>
      <TabsList>
        <TabsTrigger value="all">All</TabsTrigger>
        <TabsTrigger value="active">Active</TabsTrigger>
        <TabsTrigger value="review">Review</TabsTrigger>
        <TabsTrigger value="complete">Complete</TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
