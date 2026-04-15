"use client";

import { Bot } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { AssistantInfo } from "@/lib/agentsApi";

const GRAPH_DESCRIPTIONS: Record<string, string> = {
  needs_package: "Research → Gap → LO → Needs → Prose QA → Review",
  curriculum_package: "Needs + Curriculum + Protocol + Marketing → Review",
  grant_package: "Full 11 agents + Prose QA (2 passes) + Compliance",
  research: "Literature review, PubMed, Perplexity research",
  clinical_practice: "Standard-of-care and barrier analysis",
  gap_analysis: "Evidence-based practice gap identification",
  learning_objectives: "Moore's Framework learning objective mapping",
  needs_assessment: "Cold open narrative, 3100+ word document",
  curriculum_design: "Educational design + innovation section",
  research_protocol: "IRB-ready outcomes research protocol",
  marketing_plan: "Audience strategy + channel budget allocation",
  grant_writer: "Full grant package assembly",
  prose_quality: "De-AI-ification scoring, banned pattern detection",
  compliance_review: "ACCME verification and compliance gate",
};

const RECIPE_GRAPHS = ["needs_package", "curriculum_package", "grant_package"];

interface AssistantsRegistryProps {
  assistants: AssistantInfo[];
}

export function AssistantsRegistry({ assistants }: AssistantsRegistryProps) {
  const recipes = assistants.filter((a) => RECIPE_GRAPHS.includes(a.graphId));
  const agents = assistants.filter((a) => !RECIPE_GRAPHS.includes(a.graphId));

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <h3 className="text-sm font-semibold">Registered Graphs ({assistants.length})</h3>

      {recipes.length > 0 && (
        <div>
          <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Recipe Graphs</h4>
          <div className="grid grid-cols-2 gap-2">
            {recipes.map((a) => (
              <AssistantCard key={a.assistantId} assistant={a} />
            ))}
          </div>
        </div>
      )}

      {agents.length > 0 && (
        <div>
          <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Individual Agents</h4>
          <div className="grid grid-cols-2 gap-2">
            {agents.map((a) => (
              <AssistantCard key={a.assistantId} assistant={a} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AssistantCard({ assistant }: { assistant: AssistantInfo }) {
  const desc = GRAPH_DESCRIPTIONS[assistant.graphId] ?? "";
  const isRecipe = RECIPE_GRAPHS.includes(assistant.graphId);

  return (
    <div className="rounded-lg border border-border px-3 py-2.5">
      <div className="flex items-center gap-2">
        <Bot className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <span className="text-xs font-medium truncate">{assistant.graphId.replace(/_/g, " ")}</span>
        {isRecipe && <Badge variant="outline" className="text-[8px] ml-auto shrink-0">recipe</Badge>}
      </div>
      {desc && <p className="text-[10px] text-muted-foreground mt-1 leading-snug">{desc}</p>}
    </div>
  );
}
