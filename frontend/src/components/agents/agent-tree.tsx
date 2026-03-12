"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AgentTreeItem } from "./agent-tree-item";
import { useAgentsStore } from "@/stores/agents-store";

export function AgentTree() {
  const { agents, selectedAgent, filter, setSelected, setFilter } = useAgentsStore();

  const filtered = filter === "errors"
    ? agents.filter((a) => a.status === "error")
    : filter === "running"
      ? agents.filter((a) => ["running", "busy", "pending"].includes(a.status))
      : agents;

  return (
    <div className="w-[240px] shrink-0 border-r border-border flex flex-col h-full">
      <div className="p-3 border-b border-border">
        <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
          <TabsList className="w-full">
            <TabsTrigger value="running" className="flex-1 text-[10px]">Running</TabsTrigger>
            <TabsTrigger value="all" className="flex-1 text-[10px]">All</TabsTrigger>
            <TabsTrigger value="errors" className="flex-1 text-[10px]">Errors</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-0.5">
        {filtered.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-8">
            {filter === "running" ? "No running agents" : filter === "errors" ? "No errors" : "No agents"}
          </p>
        ) : (
          filtered.map((agent) => (
            <AgentTreeItem
              key={agent.threadId}
              agent={agent}
              selected={selectedAgent?.threadId === agent.threadId}
              onClick={() => setSelected(agent)}
            />
          ))
        )}
      </div>
    </div>
  );
}
