"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AgentOutput } from "@/types/cme";

const AGENT_LABELS: Record<string, string> = {
  research: "Research & Literature",
  research_agent: "Research & Literature",
  clinical: "Clinical Practice",
  clinical_practice_agent: "Clinical Practice",
  gap_analysis: "Gap Analysis",
  gap_analysis_agent: "Gap Analysis",
  learning_objectives: "Learning Objectives",
  learning_objectives_agent: "Learning Objectives",
  needs_assessment: "Needs Assessment",
  needs_assessment_agent: "Needs Assessment",
  curriculum: "Curriculum Design",
  curriculum_design_agent: "Curriculum Design",
  protocol: "Research Protocol",
  research_protocol_agent: "Research Protocol",
  marketing: "Marketing Plan",
  marketing_plan_agent: "Marketing Plan",
  grant_package: "Grant Writing",
  grant_writer_agent: "Grant Writing",
  prose_quality: "Prose Quality",
  prose_quality_agent: "Prose Quality",
  compliance: "Compliance Review",
  compliance_review_agent: "Compliance Review",
};

const DOCUMENT_KEYS: Record<string, string> = {
  research: "research_document",
  clinical: "clinical_practice_document",
  gap_analysis: "gap_analysis_document",
  learning_objectives: "learning_objectives_document",
  needs_assessment: "complete_document",
  curriculum: "curriculum_document",
  protocol: "protocol_document",
  marketing: "marketing_document",
  grant_writer: "complete_document_markdown",
  prose_quality_1: "summary",
  prose_quality_2: "summary",
  compliance: "compliance_report",
};

function extractDocument(agentName: string, output: AgentOutput): string | null {
  if (output.document_text && output.document_text.length > 10) return output.document_text;
  const content = output.content;
  const key = DOCUMENT_KEYS[agentName];
  if (key && typeof content[key] === "string") return content[key] as string;
  for (const k of Object.keys(content)) {
    if (k.endsWith("_document") && typeof content[k] === "string") return content[k] as string;
  }
  if (typeof content.document === "string") return content.document as string;
  if (typeof content.complete_document === "string") return content.complete_document as string;
  return null;
}

export function DocumentCard({ output }: { output: AgentOutput }) {
  const [expanded, setExpanded] = useState(false);
  const label = AGENT_LABELS[output.agent_name] ?? output.agent_name;
  const content = output.content;
  const wordCount = typeof content.word_count === "number" ? content.word_count : null;
  const doc = extractDocument(output.agent_name, output);

  return (
    <Card>
      <CardHeader
        className="pb-2 cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={`h-4 w-4 text-muted-foreground transition-transform ${expanded ? "rotate-90" : ""}`}
            />
            <CardTitle className="text-sm">{label}</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {output.quality_score !== null && (
              <Badge variant={output.quality_score >= 0.8 ? "default" : "secondary"} className="text-[10px]">
                {Math.round(output.quality_score * 100)}%
              </Badge>
            )}
            <Badge variant="outline" className="text-[10px]">{output.output_type}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {wordCount !== null && <span>{wordCount.toLocaleString()} words</span>}
          <span>{new Date(output.created_at).toLocaleString()}</span>
        </div>
        {expanded && (
          <div className="mt-4 border-t pt-4">
            {doc ? (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc}</ReactMarkdown>
              </div>
            ) : (
              <pre className="text-xs bg-muted p-4 rounded-md overflow-auto max-h-[600px]">
                {JSON.stringify(output.content, null, 2)}
              </pre>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
