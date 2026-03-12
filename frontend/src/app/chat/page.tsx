"use client";

import { useState } from "react";
import { Assistant } from "@/components/dhg/assistant";
import { GraphSelector } from "@/components/dhg/graph-selector";

export default function ChatPage() {
  const [graphId, setGraphId] = useState("needs_assessment");

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 border-b border-border px-6 py-3">
        <h2 className="text-sm font-semibold text-foreground">Chat</h2>
        <div className="h-5 w-px bg-border" />
        <GraphSelector value={graphId} onChange={setGraphId} />
      </div>
      <div className="flex-1 overflow-hidden">
        <Assistant key={graphId} graphId={graphId} />
      </div>
    </div>
  );
}
