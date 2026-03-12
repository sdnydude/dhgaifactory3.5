"use client";

import { Badge } from "@/components/ui/badge";
import type { CMEProjectDetail } from "@/types/cme";

export function SettingsTab({ project }: { project: CMEProjectDetail }) {
  const intake = project.intake as Record<string, Record<string, unknown>>;
  const sectionA = intake?.section_a;

  return (
    <div className="space-y-4">
      <h4 className="text-sm font-semibold">Project Configuration</h4>
      <div className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <span className="text-muted-foreground">Project ID</span>
          <p className="font-mono">{project.id}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Status</span>
          <p><Badge variant="outline">{project.status}</Badge></p>
        </div>
        <div>
          <span className="text-muted-foreground">Therapeutic Area</span>
          <p>{sectionA?.therapeutic_area as string ?? "N/A"}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Disease State</span>
          <p>{sectionA?.disease_state as string ?? "N/A"}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Created</span>
          <p>{new Date(project.created_at).toLocaleString()}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Updated</span>
          <p>{new Date(project.updated_at).toLocaleString()}</p>
        </div>
      </div>
      <div>
        <span className="text-xs text-muted-foreground">Available Outputs</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {project.outputs_available.length > 0
            ? project.outputs_available.map((o) => (
                <Badge key={o} variant="secondary" className="text-[10px]">{o}</Badge>
              ))
            : <p className="text-xs text-muted-foreground">None yet</p>}
        </div>
      </div>
    </div>
  );
}
