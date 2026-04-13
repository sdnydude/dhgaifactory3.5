"use client";

import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { CMEProjectDetail } from "@/types/cme";
import { CMEProjectStatus } from "@/types/cme";

const STATUS_STYLES: Record<CMEProjectStatus, { label: string; variant: "default" | "secondary" | "outline" | "destructive" }> = {
  [CMEProjectStatus.INTAKE]: { label: "Intake", variant: "secondary" },
  [CMEProjectStatus.PROCESSING]: { label: "Processing", variant: "default" },
  [CMEProjectStatus.REVIEW]: { label: "Review", variant: "outline" },
  [CMEProjectStatus.AWAITING_REVIEW]: { label: "Awaiting Review", variant: "outline" },
  [CMEProjectStatus.COMPLETE]: { label: "Complete", variant: "secondary" },
  [CMEProjectStatus.FAILED]: { label: "Failed", variant: "destructive" },
  [CMEProjectStatus.CANCELLED]: { label: "Cancelled", variant: "secondary" },
  [CMEProjectStatus.ARCHIVED]: { label: "Archived", variant: "secondary" },
};

export function ProjectCard({ project }: { project: CMEProjectDetail }) {
  const statusInfo = STATUS_STYLES[project.status] ?? STATUS_STYLES[CMEProjectStatus.INTAKE];
  const rawArea = (project.intake as Record<string, Record<string, unknown>>)?.section_a?.therapeutic_area;
  const therapeuticArea = Array.isArray(rawArea) ? rawArea.join(", ") : typeof rawArea === "string" ? rawArea : null;

  return (
    <Link href={`/projects/${project.id}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-sm font-medium leading-snug line-clamp-2">
              {project.name}
            </CardTitle>
            <Badge variant={statusInfo.variant} className="shrink-0 text-[10px]">
              {statusInfo.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {therapeuticArea && (
            <p className="text-xs text-muted-foreground">{therapeuticArea}</p>
          )}
          <div className="space-y-1">
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>{project.current_agent ? `Running: ${project.current_agent}` : "Idle"}</span>
              <span>{project.progress_percent}%</span>
            </div>
            <Progress value={project.progress_percent} className="h-1.5" />
          </div>
          <p className="text-[10px] text-muted-foreground">
            {new Date(project.created_at).toLocaleDateString()}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}
