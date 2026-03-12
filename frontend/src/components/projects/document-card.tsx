"use client";

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

export function DocumentCard({ output }: { output: AgentOutput }) {
  const label = AGENT_LABELS[output.agent_name] ?? output.agent_name;
  const content = output.content;
  const wordCount = typeof content.word_count === "number" ? content.word_count : null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">{label}</CardTitle>
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
      </CardContent>
    </Card>
  );
}
