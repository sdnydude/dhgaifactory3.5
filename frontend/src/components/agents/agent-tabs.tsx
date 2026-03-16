"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { PipelineProgress } from "./pipeline-progress";
import { StreamTab } from "./stream-tab";
import { DetailTab } from "./detail-tab";
import { VsTab } from "./vs-tab";
import { OutputsTab } from "./outputs-tab";
import { TimelineTab } from "./timeline-tab";
import { useAgentsStore } from "@/stores/agents-store";
import type { RunningAgent, ThreadState } from "@/lib/agentsApi";

function statusBadgeVariant(status: string) {
  if (status === "running" || status === "in_progress" || status === "busy")
    return "default" as const;
  if (status === "success" || status === "complete") return "secondary" as const;
  if (status === "error" || status === "failed") return "destructive" as const;
  return "outline" as const;
}

function autoTab(agent: RunningAgent | null): string {
  if (!agent) return "detail";
  const s = agent.status;
  if (s === "busy") return "stream";
  if (s === "error" || s === "failed" || s === "interrupted") return "detail";
  return "outputs";
}

interface AgentTabsProps {
  agent: RunningAgent;
  state: ThreadState | null;
}

export function AgentTabs({ agent, state }: AgentTabsProps) {
  const streamStatus = useAgentsStore((s) => s.streamStatus);
  const [tab, setTab] = useState(() => autoTab(agent));
  const [prevThreadId, setPrevThreadId] = useState(agent.threadId);

  // Reset tab on thread switch
  if (agent.threadId !== prevThreadId) {
    setPrevThreadId(agent.threadId);
    setTab(autoTab(agent));
  }

  // Auto-start stream for busy threads
  const startStream = useAgentsStore((s) => s.startStream);
  useEffect(() => {
    if (agent.status === "busy") {
      startStream(agent.threadId);
    }
    return () => {
      useAgentsStore.getState().stopStream();
    };
  }, [agent.threadId, agent.status, startStream]);

  const isStreaming = streamStatus === "streaming" || streamStatus === "connecting";

  return (
    <div className="flex flex-col h-full overflow-hidden p-4">
      {/* Persistent header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold">{agent.graphId}</h3>
          {state?.projectName && (
            <p className="text-xs text-muted-foreground mt-0.5">{state.projectName}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={statusBadgeVariant(agent.status)}>{agent.status}</Badge>
          {state?.humanReviewStatus && (
            <Badge variant="outline" className="text-[9px]">
              Review: {state.humanReviewStatus}
            </Badge>
          )}
        </div>
      </div>

      {/* Pipeline progress — always visible */}
      {state && <PipelineProgress state={state} graphId={agent.graphId} />}

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab} className="flex flex-col flex-1 overflow-hidden mt-3">
        <TabsList className="w-full justify-start">
          <TabsTrigger value="stream" className="relative">
            Stream
            {isStreaming && (
              <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-orange-500 animate-pulse" />
            )}
          </TabsTrigger>
          <TabsTrigger value="detail">Detail</TabsTrigger>
          <TabsTrigger value="vs">VS</TabsTrigger>
          <TabsTrigger value="outputs">Outputs</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
        </TabsList>

        <TabsContent value="stream" className="flex-1 overflow-hidden mt-2">
          <StreamTab agent={agent} />
        </TabsContent>
        <TabsContent value="detail" className="flex-1 overflow-auto mt-2">
          <DetailTab agent={agent} state={state} />
        </TabsContent>
        <TabsContent value="vs" className="flex-1 overflow-auto mt-2">
          <VsTab state={state} />
        </TabsContent>
        <TabsContent value="outputs" className="flex-1 overflow-auto mt-2">
          <OutputsTab agent={agent} state={state} />
        </TabsContent>
        <TabsContent value="timeline" className="flex-1 overflow-auto mt-2">
          <TimelineTab agent={agent} state={state} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
