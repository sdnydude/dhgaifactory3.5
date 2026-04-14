"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";
import { IntakeForm } from "@/components/intake/intake-form";
import { CMEProjectStatus } from "@/types/cme";
import type { IntakeSubmission } from "@/types/cme";
import * as registryApi from "@/lib/registryApi";

export default function EditProjectPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const [initialIntake, setInitialIntake] = useState<IntakeSubmission | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    registryApi.getProject(projectId).then((project) => {
      if (
        project.status === CMEProjectStatus.PROCESSING ||
        project.status === CMEProjectStatus.ARCHIVED
      ) {
        router.replace(`/projects/${projectId}`);
        return;
      }
      setInitialIntake(project.intake as unknown as IntakeSubmission);
      setLoading(false);
    }).catch(() => {
      router.replace("/projects");
    });
  }, [projectId, router]);

  if (loading || !initialIntake) {
    return (
      <div className="flex h-full">
        <div className="w-[220px] border-r border-border p-3 space-y-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
        <div className="flex-1 p-6">
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  return (
    <IntakeForm
      mode="edit"
      projectId={projectId}
      initialIntake={initialIntake}
    />
  );
}
