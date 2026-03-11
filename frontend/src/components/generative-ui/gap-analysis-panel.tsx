"use client";

import { useCopilotAction } from "@copilotkit/react-core";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Gap {
  gap_statement: string;
  evidence_summary: string;
  severity: string;
}

export function GapAnalysisPanel() {
  useCopilotAction({
    name: "renderGapAnalysis",
    description:
      "Display structured gap analysis results with identified practice gaps",
    parameters: [
      {
        name: "gaps_json",
        type: "string",
        description: "JSON array of identified gaps",
      },
      { name: "gap_count", type: "number", description: "Number of gaps found" },
      {
        name: "therapeutic_area",
        type: "string",
        description: "Therapeutic area analyzed",
      },
    ],
    handler: async () => {
      return "Gap analysis rendered";
    },
    render: ({ args, status }) => {
      const isComplete = status === "complete";
      let gaps: Gap[] = [];

      try {
        if (args.gaps_json) {
          gaps = JSON.parse(args.gaps_json as string);
        }
      } catch {
        /* gaps stays empty */
      }

      return (
        <Card className="my-3 border-dhg-purple/20">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Gap Analysis</CardTitle>
              <Badge variant="outline">
                {isComplete
                  ? `${(args.gap_count as number) ?? gaps.length} gaps identified`
                  : "Analyzing..."}
              </Badge>
            </div>
            {args.therapeutic_area && (
              <p className="text-xs text-muted-foreground">
                {args.therapeutic_area as string}
              </p>
            )}
          </CardHeader>
          <CardContent>
            {gaps.length > 0 ? (
              <div className="space-y-2">
                {gaps.map((gap, i) => (
                  <div
                    key={i}
                    className="rounded-md bg-muted p-2.5 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Gap {i + 1}</span>
                      {gap.severity && (
                        <Badge
                          variant="secondary"
                          className="text-[10px] px-1.5 py-0"
                        >
                          {gap.severity}
                        </Badge>
                      )}
                    </div>
                    <p>{gap.gap_statement}</p>
                    {gap.evidence_summary && (
                      <p className="text-muted-foreground">
                        {gap.evidence_summary}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              !isComplete && (
                <p className="text-xs text-muted-foreground">
                  Identifying evidence-based practice gaps...
                </p>
              )
            )}
          </CardContent>
        </Card>
      );
    },
  });

  return null;
}
