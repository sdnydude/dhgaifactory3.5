"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
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

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  [CMEProjectStatus.PROCESSING]: "default",
  [CMEProjectStatus.REVIEW]: "secondary",
  [CMEProjectStatus.AWAITING_REVIEW]: "secondary",
  [CMEProjectStatus.COMPLETE]: "default",
  [CMEProjectStatus.FAILED]: "destructive",
  [CMEProjectStatus.CANCELLED]: "outline",
  [CMEProjectStatus.INTAKE]: "outline",
};

export function ProjectHeader({ project }: { project: CMEProjectDetail }) {
  const variant = STATUS_VARIANTS[project.status] ?? "outline";
  const isFailed = project.status === CMEProjectStatus.FAILED;

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
