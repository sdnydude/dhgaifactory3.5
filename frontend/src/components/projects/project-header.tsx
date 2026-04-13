"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Archive, Pencil } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { CMEProjectStatus } from "@/types/cme";
import type { CMEProjectDetail } from "@/types/cme";
import { useProjectsStore } from "@/stores/projects-store";

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  [CMEProjectStatus.PROCESSING]: "default",
  [CMEProjectStatus.REVIEW]: "secondary",
  [CMEProjectStatus.AWAITING_REVIEW]: "secondary",
  [CMEProjectStatus.COMPLETE]: "default",
  [CMEProjectStatus.FAILED]: "destructive",
  [CMEProjectStatus.CANCELLED]: "outline",
  [CMEProjectStatus.INTAKE]: "outline",
  [CMEProjectStatus.ARCHIVED]: "secondary",
};

export function ProjectHeader({ project }: { project: CMEProjectDetail }) {
  const router = useRouter();
  const { archiveProject } = useProjectsStore();
  const [archiving, setArchiving] = useState(false);
  const variant = STATUS_VARIANTS[project.status] ?? "outline";
  const isFailed = project.status === CMEProjectStatus.FAILED;
  const canEdit = project.status === CMEProjectStatus.INTAKE;
  const canArchive = project.status !== CMEProjectStatus.ARCHIVED;

  async function handleArchive() {
    setArchiving(true);
    await archiveProject(project.id);
    router.push("/projects");
  }

  return (
    <div className="border-b border-border px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink render={<Link href="/projects" />}>
                  Projects
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{project.name}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
        <div className="flex items-center gap-2">
          {canEdit && (
            <Link href={`/projects/${project.id}/edit`}>
              <Button variant="outline" size="sm" className="gap-1.5">
                <Pencil className="h-3 w-3" />
                Edit
              </Button>
            </Link>
          )}
          {canArchive && (
            <Dialog>
              <DialogTrigger
                render={
                  <Button variant="outline" size="sm" className="gap-1.5 text-muted-foreground hover:text-destructive hover:border-destructive/50">
                    <Archive className="h-3 w-3" />
                    Archive
                  </Button>
                }
              />
              <DialogContent showCloseButton={false}>
                <DialogHeader>
                  <DialogTitle>Archive project?</DialogTitle>
                  <DialogDescription>
                    This will move &ldquo;{project.name}&rdquo; to the archive. The project and its outputs will be preserved but hidden from the active list.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button variant="outline" onClick={handleArchive} disabled={archiving}>
                    {archiving ? "Archiving..." : "Archive"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
          <Badge variant={variant} className="text-[10px]">{project.status}</Badge>
          <span className="text-xs text-muted-foreground">{project.progress_percent}%</span>
        </div>
      </div>
      {isFailed && (
        <p className="mt-1 text-xs text-destructive">
          Pipeline failed — check the Activity tab for error details.
        </p>
      )}
    </div>
  );
}
