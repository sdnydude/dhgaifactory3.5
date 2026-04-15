"use client";

import { useEffect } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { useFilesTabStore } from "@/stores/files-tab-store";
import { listProjectDocuments } from "@/lib/filesApi";

export function FilesTree() {
  const projects = useFilesTabStore((s) => s.projects);
  const documentsByProject = useFilesTabStore((s) => s.documentsByProject);
  const expandedProjectIds = useFilesTabStore((s) => s.expandedProjectIds);
  const selectedDocumentIds = useFilesTabStore((s) => s.selectedDocumentIds);
  const toggleProjectExpanded = useFilesTabStore((s) => s.toggleProjectExpanded);
  const toggleDocumentSelected = useFilesTabStore((s) => s.toggleDocumentSelected);
  const setDocuments = useFilesTabStore((s) => s.setDocuments);
  const setPreview = useFilesTabStore((s) => s.setPreview);

  useEffect(() => {
    let active = true;
    expandedProjectIds.forEach(async (pid) => {
      if (documentsByProject[pid]) return;
      try {
        const res = await listProjectDocuments(pid);
        if (!active) return;
        setDocuments(pid, res.documents);
      } catch (err) {
        console.error("Failed to load project documents", pid, err);
      }
    });
    return () => {
      active = false;
    };
  }, [expandedProjectIds, documentsByProject, setDocuments]);

  if (projects.length === 0) {
    return (
      <div className="flex-1 p-4 text-xs text-muted-foreground">
        No projects.
      </div>
    );
  }

  return (
    <ul className="flex-1 overflow-y-auto">
      {projects.map((project) => {
        const expanded = expandedProjectIds.includes(project.id);
        const docs = documentsByProject[project.id] ?? [];
        return (
          <li key={project.id} className="border-b border-border">
            <button
              type="button"
              onClick={() => toggleProjectExpanded(project.id)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted"
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4 shrink-0" />
              ) : (
                <ChevronRight className="h-4 w-4 shrink-0" />
              )}
              <span className="flex-1 truncate">{project.name}</span>
              <span className="text-xs text-muted-foreground">
                {project.document_count} docs
              </span>
            </button>
            {expanded && (
              <ul className="bg-background">
                {docs.length === 0 ? (
                  <li className="px-6 py-1.5 text-xs text-muted-foreground">
                    Loading…
                  </li>
                ) : (
                  docs.map((doc, i) => {
                    const checked = selectedDocumentIds.includes(doc.id);
                    return (
                      <li
                        key={doc.id}
                        className="flex items-center gap-2 px-6 py-1.5 text-xs hover:bg-muted"
                      >
                        <Checkbox
                          checked={checked}
                          onCheckedChange={() =>
                            toggleDocumentSelected(project.id, doc.id)
                          }
                        />
                        <button
                          type="button"
                          onClick={() => setPreview(doc.id)}
                          className="flex-1 truncate text-left"
                        >
                          <span className="mr-2 text-muted-foreground tabular-nums">
                            {String(i + 1).padStart(2, "0")}
                          </span>
                          {doc.title ?? doc.document_type}
                        </button>
                        <span className="text-muted-foreground tabular-nums">
                          {doc.word_count ?? "—"}w
                        </span>
                      </li>
                    );
                  })
                )}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}
