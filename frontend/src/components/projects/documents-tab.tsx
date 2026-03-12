"use client";

import { FileText } from "lucide-react";
import { DocumentCard } from "./document-card";
import type { AgentOutput } from "@/types/cme";

export function DocumentsTab({ outputs }: { outputs: AgentOutput[] }) {
  if (outputs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <FileText className="h-10 w-10 text-muted-foreground/50 mb-3" />
        <p className="text-sm text-muted-foreground">No documents yet</p>
        <p className="text-xs text-muted-foreground">Documents will appear as agents complete their work.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {outputs.map((output) => (
        <DocumentCard key={output.agent_name} output={output} />
      ))}
    </div>
  );
}
