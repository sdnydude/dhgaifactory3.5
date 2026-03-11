"use client";

import { useCopilotAction } from "@copilotkit/react-core";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface NeedsAssessmentData {
  therapeutic_area: string;
  disease_state: string;
  target_audience: string;
  word_count: number;
  prose_density: number;
  quality_passed: boolean;
  sections: Record<string, number>;
}

export function NeedsAssessmentPanel() {
  useCopilotAction({
    name: "renderNeedsAssessment",
    description:
      "Display structured needs assessment results with quality metrics",
    parameters: [
      {
        name: "therapeutic_area",
        type: "string",
        description: "Therapeutic area",
      },
      {
        name: "disease_state",
        type: "string",
        description: "Disease state",
      },
      {
        name: "word_count",
        type: "number",
        description: "Total word count",
      },
      {
        name: "prose_density",
        type: "number",
        description: "Prose density score (0-1)",
      },
      {
        name: "quality_passed",
        type: "boolean",
        description: "Whether quality gate passed",
      },
    ],
    handler: async () => {
      return "Needs assessment rendered";
    },
    render: ({ args, status }) => {
      const data = args as unknown as Partial<NeedsAssessmentData>;
      const isComplete = status === "complete";

      return (
        <Card className="my-3 border-dhg-purple/20">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">
                Needs Assessment Results
              </CardTitle>
              {isComplete && (
                <Badge
                  variant={data.quality_passed ? "default" : "destructive"}
                  className={
                    data.quality_passed ? "bg-green-600" : "bg-red-600"
                  }
                >
                  {data.quality_passed ? "QA Passed" : "QA Failed"}
                </Badge>
              )}
              {!isComplete && (
                <Badge variant="secondary">Processing...</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              {data.therapeutic_area && (
                <div>
                  <span className="text-muted-foreground">
                    Therapeutic Area:
                  </span>
                  <p className="font-medium">{data.therapeutic_area}</p>
                </div>
              )}
              {data.disease_state && (
                <div>
                  <span className="text-muted-foreground">Disease State:</span>
                  <p className="font-medium">{data.disease_state}</p>
                </div>
              )}
            </div>
            {isComplete && (
              <div className="flex gap-4 pt-2 border-t border-border text-xs">
                <div>
                  <span className="text-muted-foreground">Words:</span>{" "}
                  <span className="font-mono">
                    {data.word_count?.toLocaleString() ?? "—"}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Density:</span>{" "}
                  <span className="font-mono">
                    {data.prose_density
                      ? `${(data.prose_density * 100).toFixed(1)}%`
                      : "—"}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      );
    },
  });

  return null;
}
