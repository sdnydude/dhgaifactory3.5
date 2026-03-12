"use client";

import { useEffect, useRef } from "react";
import { AgentTree } from "@/components/agents/agent-tree";
import { AgentDetail } from "@/components/agents/agent-detail";
import { StatsBar } from "@/components/agents/stats-bar";
import { AssistantsRegistry } from "@/components/agents/assistants-registry";
import { useAgentsStore } from "@/stores/agents-store";

export default function AgentsPage() {
  const {
    selectedAgent,
    selectedState,
    assistants,
    stats,
    filter,
    fetchRunning,
    fetchAll,
    fetchAssistants,
    fetchStats,
    fetchThreadState,
  } = useAgentsStore();
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    fetchAssistants();
    fetchStats();
  }, [fetchAssistants, fetchStats]);

  useEffect(() => {
    const fetch = filter === "all" ? fetchAll : fetchRunning;
    fetch();
    fetchStats();
    intervalRef.current = setInterval(() => {
      fetch();
      fetchStats();
    }, 5000);
    return () => clearInterval(intervalRef.current);
  }, [filter, fetchRunning, fetchAll, fetchStats]);

  useEffect(() => {
    if (!selectedAgent) return;
    fetchThreadState(selectedAgent.threadId);
    const id = setInterval(() => fetchThreadState(selectedAgent.threadId), 5000);
    return () => clearInterval(id);
  }, [selectedAgent, fetchThreadState]);

  const showRegistry = !selectedAgent;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StatsBar stats={stats} />
      <div className="flex flex-1 overflow-hidden">
        <AgentTree />
        <div className="flex-1 overflow-hidden">
          {showRegistry ? (
            <AssistantsRegistry assistants={assistants} />
          ) : (
            <AgentDetail agent={selectedAgent} state={selectedState} />
          )}
        </div>
      </div>
    </div>
  );
}
