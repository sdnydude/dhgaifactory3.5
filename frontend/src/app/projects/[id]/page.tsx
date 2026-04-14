"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectHeader } from "@/components/projects/project-header";
import { PipelineNav } from "@/components/projects/pipeline-nav";
import { ProjectTabs } from "@/components/projects/project-tabs";
import { StepContent } from "@/components/projects/step-content";
import { RunStatusBanner } from "@/components/projects/run-status-banner";
import { PIPELINE_STEPS } from "@/types/cme";
import { CMEProjectStatus } from "@/types/cme";
import type { AgentOutput, ExecutionStatus } from "@/types/cme";
import { useProjectsStore } from "@/stores/projects-store";
import * as registryApi from "@/lib/registryApi";

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { currentProject, pipelineStatus, fetchProject, fetchPipelineStatus, fetchRuns, clearCurrent } = useProjectsStore();
  const [outputs, setOutputs] = useState<AgentOutput[]>([]);
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
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
        <div className="flex-1 flex">
          <div className="w-[220px] border-r border-border p-3 space-y-2">
            {Array.from({ length: 14 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
          <div className="flex-1 p-6">
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  function getStepStatus(stepId: string): "completed" | "active" | "pending" | "error" {
    if (!pipelineStatus) return "pending";
    if (pipelineStatus.agents_completed.some((a) => a === stepId || stepId.startsWith(a))) return "completed";
    if (pipelineStatus.current_agent === stepId) return "active";
    return "pending";
  }

  const selectedStepDef = selectedStep ? PIPELINE_STEPS.find((s) => s.id === selectedStep) : null;
  const selectedOutput = selectedStep
    ? outputs.find((o) => o.agent_name === selectedStep || o.agent_name === selectedStepDef?.agent) ?? null
    : null;

  return (
    <div className="flex flex-col h-full">
      <ProjectHeader project={currentProject} />
      <RunStatusBanner project={currentProject} />
      <div className="flex-1 flex overflow-hidden">
        <PipelineNav
          pipelineStatus={pipelineStatus}
          selectedStep={selectedStep}
          onSelectStep={setSelectedStep}
        />
        <div className="flex-1 overflow-hidden">
          {selectedStep && selectedStepDef ? (
            <div className="p-4 overflow-auto h-full">
              <StepContent
                stepId={selectedStep}
                stepLabel={selectedStepDef.label}
                status={getStepStatus(selectedStep)}
                output={selectedOutput}
              />
            </div>
          ) : (
            <ProjectTabs
              project={currentProject}
              pipelineStatus={pipelineStatus}
              outputs={outputs}
            />
          )}
        </div>
      </div>
    </div>
  );
}
