"use client";

import { useEffect, useRef, useState } from "react";
import { FolderKanban, Plus } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ProjectCard } from "./project-card";
import { ProjectFilters, type ProjectFilter } from "./project-filters";
import { useProjectsStore } from "@/stores/projects-store";
import { CMEProjectStatus } from "@/types/cme";
import * as registryApi from "@/lib/registryApi";

const FILTER_MAP: Record<ProjectFilter, CMEProjectStatus[] | null> = {
  all: null,
  active: [CMEProjectStatus.INTAKE, CMEProjectStatus.PROCESSING],
  review: [CMEProjectStatus.REVIEW],
  complete: [CMEProjectStatus.COMPLETE],
  archived: [CMEProjectStatus.ARCHIVED],
};

export function ProjectBoard() {
  const { projects, loading, error, fetchProjects } = useProjectsStore();
  const [filter, setFilter] = useState<ProjectFilter>("all");
  const [archivedProjects, setArchivedProjects] = useState<typeof projects>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    fetchProjects();
    intervalRef.current = setInterval(fetchProjects, 15000);
    return () => clearInterval(intervalRef.current);
  }, [fetchProjects]);

  // Fetch archived projects separately (excluded from default list)
  useEffect(() => {
    if (filter === "archived") {
      registryApi.listProjects(CMEProjectStatus.ARCHIVED).then(setArchivedProjects).catch(() => {});
    }
  }, [filter]);

  const displayProjects = filter === "archived" ? archivedProjects : projects;
  const filtered = FILTER_MAP[filter] && filter !== "archived"
    ? displayProjects.filter((p) => FILTER_MAP[filter]!.includes(p.status))
    : displayProjects;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-foreground">Projects</h2>
          <ProjectFilters value={filter} onChange={setFilter} />
        </div>
        <Link href="/projects/new">
          <Button size="sm" className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            New Project
          </Button>
        </Link>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {error && (
          <div className="rounded-md bg-destructive/10 text-destructive text-sm p-3 mb-4">
            {error}
          </div>
        )}

        {loading && projects.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-[140px] rounded-lg bg-muted animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <FolderKanban className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-sm font-medium text-foreground mb-1">No projects yet</h3>
            <p className="text-xs text-muted-foreground mb-4">
              Create your first CME project to get started.
            </p>
            <Link href="/projects/new">
              <Button size="sm" className="gap-1.5">
                <Plus className="h-3.5 w-3.5" />
                New Project
              </Button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
