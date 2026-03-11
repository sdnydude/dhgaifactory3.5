"use client";

import { useState } from "react";
import { Header } from "@/components/dhg/header";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { NeedsAssessmentPanel } from "@/components/generative-ui/needs-assessment-panel";
import { GapAnalysisPanel } from "@/components/generative-ui/gap-analysis-panel";
import "@copilotkit/react-ui/styles.css";

const STUDIO_AGENTS = [
  { id: "needs_assessment", label: "Needs Assessment" },
  { id: "gap_analysis", label: "Gap Analysis" },
  { id: "needs_package", label: "Needs Package" },
  { id: "grant_package", label: "Grant Package" },
];

export default function StudioPage() {
  const [selectedAgent, setSelectedAgent] = useState(STUDIO_AGENTS[0].id);

  return (
    <div className="flex flex-col h-dvh bg-background">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <div className="w-56 border-r border-border p-4 space-y-2">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Agent
          </h2>
          {STUDIO_AGENTS.map((agent) => (
            <button
              key={agent.id}
              onClick={() => setSelectedAgent(agent.id)}
              className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                selectedAgent === agent.id
                  ? "bg-dhg-purple text-white"
                  : "text-foreground hover:bg-muted"
              }`}
            >
              {agent.label}
            </button>
          ))}
        </div>

        <div className="flex-1">
          <CopilotKit runtimeUrl="/api/copilotkit" agent={selectedAgent}>
            <NeedsAssessmentPanel />
            <GapAnalysisPanel />
            <CopilotChat
              labels={{
                title: `Studio — ${STUDIO_AGENTS.find((a) => a.id === selectedAgent)?.label}`,
                initial: "Run an agent to see generative UI panels inline.",
              }}
            />
          </CopilotKit>
        </div>
      </div>
    </div>
  );
}
