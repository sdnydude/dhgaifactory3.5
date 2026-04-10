"use client";

import { useEffect, useRef } from "react";
import { AgentTree } from "@/components/agents/agent-tree";
import { AgentTabs } from "@/components/agents/agent-tabs";
import { StatsBar } from "@/components/agents/stats-bar";
import { AgentsLibrary } from "@/components/agents/agents-library";
import { useAgentsStore } from "@/stores/agents-store";

export default function AgentsPage() {
  const {
    selectedAgent,
    selectedState,
    stats,
    filter,
    fetchRunning,
    fetchAll,
    fetchStats,
    fetchThreadState,
  } = useAgentsStore();
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

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

  const showLibrary = !selectedAgent;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StatsBar stats={stats} />
      <div className="flex flex-1 overflow-hidden">
        <AgentTree />
        <div className="flex-1 overflow-hidden">
          {showLibrary ? (
            <AgentsLibrary />
          ) : (
            <AgentTabs agent={selectedAgent} state={selectedState} />
          )}
        </div>
      </div>
    </div>
  );
}
