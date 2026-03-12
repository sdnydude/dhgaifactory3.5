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
import type { CMEProjectDetail } from "@/types/cme";

export function ProjectHeader({ project }: { project: CMEProjectDetail }) {
  return (
    <div className="flex items-center justify-between border-b border-border px-6 py-3">
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
        <Badge variant="outline" className="text-[10px]">{project.status}</Badge>
        <span className="text-xs text-muted-foreground">{project.progress_percent}%</span>
      </div>
    </div>
  );
}
