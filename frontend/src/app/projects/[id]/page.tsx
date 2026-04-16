"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectHeader } from "@/components/projects/project-header";
import { ProjectTabs } from "@/components/projects/project-tabs";
import { RunStatusBanner } from "@/components/projects/run-status-banner";
import { CMEProjectStatus } from "@/types/cme";
import type { AgentOutput } from "@/types/cme";
import { useProjectsStore } from "@/stores/projects-store";
import * as registryApi from "@/lib/registryApi";

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { currentProject, pipelineStatus, fetchProject, fetchPipelineStatus, fetchRuns, clearCurrent } = useProjectsStore();
  const [outputs, setOutputs] = useState<AgentOutput[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    fetchProject(projectId);
    fetchPipelineStatus(projectId);
    fetchRuns(projectId);
    registryApi.listOutputs(projectId).then(setOutputs).catch(() => {});

    return () => {
      clearCurrent();
      clearInterval(intervalRef.current);
    };
  }, [projectId, fetchProject, fetchPipelineStatus, fetchRuns, clearCurrent]);

  useEffect(() => {
    if (
      currentProject &&
      (currentProject.status === CMEProjectStatus.PROCESSING || currentProject.status === CMEProjectStatus.REVIEW)
    ) {
      intervalRef.current = setInterval(() => {
        fetchProject(projectId);
        fetchPipelineStatus(projectId);
        registryApi.listOutputs(projectId).then(setOutputs).catch(() => {});
      }, 10000);
    }
    return () => clearInterval(intervalRef.current);
  }, [currentProject, projectId, fetchProject, fetchPipelineStatus]);

  if (!currentProject) {
    return (
      <div className="flex flex-col h-full">
        <div className="border-b border-border px-6 py-3">
          <Skeleton className="h-5 w-48" />
        </div>
        <div className="flex-1 p-6">
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <ProjectHeader project={currentProject} />
      <RunStatusBanner project={currentProject} />
      <div className="flex-1 overflow-hidden">
        <ProjectTabs
          project={currentProject}
          pipelineStatus={pipelineStatus}
          outputs={outputs}
        />
      </div>
    </div>
  );
}
