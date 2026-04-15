"use client";

import { useEffect } from "react";
import { Input } from "@/components/ui/input";
import { listProjects } from "@/lib/filesApi";
import { useFilesTabStore } from "@/stores/files-tab-store";
import { FilesTree } from "./files-tree";
import { FilesSelectionBar } from "./files-selection-bar";

export function FilesTab() {
  const searchQuery = useFilesTabStore((s) => s.searchQuery);
  const setSearch = useFilesTabStore((s) => s.setSearch);
  const setProjects = useFilesTabStore((s) => s.setProjects);

  useEffect(() => {
    let active = true;
    const t = setTimeout(async () => {
      try {
        const res = await listProjects({
          search: searchQuery || undefined,
          limit: 50,
        });
        if (!active) return;
        setProjects(res.projects);
      } catch (err) {
        console.error("Failed to load projects", err);
      }
    }, 200);
    return () => {
      active = false;
      clearTimeout(t);
    };
  }, [searchQuery, setProjects]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-2">
        <Input
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <FilesTree />
      <FilesSelectionBar />
    </div>
  );
}
