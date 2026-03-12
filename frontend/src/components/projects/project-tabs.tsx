"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DocumentsTab } from "./documents-tab";
import { ActivityTab } from "./activity-tab";
import { ReviewsTab } from "./reviews-tab";
import { SettingsTab } from "./settings-tab";
import type { CMEProjectDetail, ExecutionStatus, AgentOutput } from "@/types/cme";

interface ProjectTabsProps {
  project: CMEProjectDetail;
  pipelineStatus: ExecutionStatus | null;
  outputs: AgentOutput[];
}

export function ProjectTabs({ project, pipelineStatus, outputs }: ProjectTabsProps) {
  return (
    <Tabs defaultValue="documents" className="flex flex-col h-full">
      <TabsList className="mx-4 mt-3 w-fit">
        <TabsTrigger value="documents">Documents</TabsTrigger>
        <TabsTrigger value="activity">Activity</TabsTrigger>
        <TabsTrigger value="reviews">Reviews</TabsTrigger>
        <TabsTrigger value="settings">Settings</TabsTrigger>
      </TabsList>
      <TabsContent value="documents" className="flex-1 overflow-auto p-4">
        <DocumentsTab outputs={outputs} />
      </TabsContent>
      <TabsContent value="activity" className="flex-1 overflow-auto p-4">
        <ActivityTab status={pipelineStatus} />
      </TabsContent>
      <TabsContent value="reviews" className="flex-1 overflow-auto p-4">
        <ReviewsTab project={project} />
      </TabsContent>
      <TabsContent value="settings" className="flex-1 overflow-auto p-4">
        <SettingsTab project={project} />
      </TabsContent>
    </Tabs>
  );
}
