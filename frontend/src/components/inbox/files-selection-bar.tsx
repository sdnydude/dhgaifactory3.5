"use client";

import { useFilesTabStore } from "@/stores/files-tab-store";
import { Button } from "@/components/ui/button";
import { createBundleJob } from "@/lib/filesApi";
import { useDownloadsStore } from "@/stores/downloads-store";

export function FilesSelectionBar() {
  const selectedDocumentIds = useFilesTabStore((s) => s.selectedDocumentIds);
  const selectedProjectId = useFilesTabStore((s) => s.selectedProjectId);
  const clearSelection = useFilesTabStore((s) => s.clearSelection);
  const upsertJob = useDownloadsStore((s) => s.upsertJob);
  const openTray = useDownloadsStore((s) => s.openTray);

  async function onDownload() {
    if (!selectedProjectId || selectedDocumentIds.length === 0) return;
    try {
      const job = await createBundleJob({
        project_id: selectedProjectId,
        document_ids: selectedDocumentIds,
        include_manifest: true,
        include_intake: false,
      });
      upsertJob(job);
      openTray();
      clearSelection();
    } catch (err) {
      console.error("Failed to create bundle job", err);
    }
  }

  if (selectedDocumentIds.length === 0) return null;

  return (
    <div className="flex items-center justify-between border-t border-border bg-card px-4 py-2">
      <span className="text-sm text-muted-foreground">
        {selectedDocumentIds.length} selected
      </span>
      <Button size="sm" onClick={onDownload}>
        Download zip
      </Button>
    </div>
  );
}
