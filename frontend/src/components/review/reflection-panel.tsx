"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Brain,
  BarChart3,
  Shield,
} from "lucide-react";
import type { ReviewMetrics } from "./types";

interface ReflectionPanelProps {
  metrics: ReviewMetrics;
  recipe: string;
  reviewRound: number;
}

function QualitySignal({
  label,
  passed,
  detail,
}: {
  label: string;
  passed: boolean | undefined;
  detail?: string;
}) {
  const Icon = passed === true ? CheckCircle : passed === false ? XCircle : AlertTriangle;
  const color = passed === true ? "text-green-600" : passed === false ? "text-red-600" : "text-yellow-600";

  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon className={`h-4 w-4 ${color}`} />
      <span className="font-medium">{label}</span>
      {detail && <span className="text-muted-foreground">({detail})</span>}
    </div>
  );
}

function buildRecommendation(metrics: ReviewMetrics): {
  decision: "approve" | "revise" | "needs_attention";
  reasoning: string;
} {
  const issues: string[] = [];

  if (metrics.quality_passed === false) {
    issues.push("prose quality gate failed");
  }
  if (metrics.banned_patterns_found && metrics.banned_patterns_found.length > 0) {
    issues.push(`${metrics.banned_patterns_found.length} banned patterns detected`);
  }
  if (metrics.compliance_result) {
    const compliance = metrics.compliance_result as Record<string, unknown>;
    if (compliance.passed === false) {
      issues.push("ACCME compliance check failed");
    }
  }

  if (issues.length === 0) {
    return {
      decision: "approve",
      reasoning: `All quality gates passed. Word count: ${metrics.word_count ?? "N/A"}. Prose density: ${metrics.prose_density ? `${(metrics.prose_density * 100).toFixed(0)}%` : "N/A"}. No banned patterns detected. Compliance verified.`,
    };
  }

  return {
    decision: issues.length >= 2 ? "needs_attention" : "revise",
    reasoning: `Issues found: ${issues.join("; ")}. Review carefully before approving.`,
  };
}

export function ReflectionPanel({ metrics, recipe, reviewRound }: ReflectionPanelProps) {
  const recommendation = buildRecommendation(metrics);

  const recBadgeVariant =
    recommendation.decision === "approve"
      ? "default"
      : recommendation.decision === "revise"
        ? "secondary"
        : "destructive";

  const recLabel =
    recommendation.decision === "approve"
      ? "Recommend Approve"
      : recommendation.decision === "revise"
        ? "Suggest Revision"
        : "Needs Attention";

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Brain className="h-4 w-4 text-dhg-purple" />
            AI Reflection
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[10px]">
              Round {reviewRound}
            </Badge>
            <Badge variant={recBadgeVariant} className="text-[10px]">
              {recLabel}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Quality Signals */}
        <div>
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <BarChart3 className="h-3 w-3" />
            Quality Signals
          </div>
          <div className="space-y-1.5">
            <QualitySignal
              label="Prose Quality"
              passed={metrics.quality_passed}
              detail={metrics.word_count ? `${metrics.word_count} words` : undefined}
            />
            <QualitySignal
              label="Banned Patterns"
              passed={!metrics.banned_patterns_found?.length}
              detail={
                metrics.banned_patterns_found?.length
                  ? `${metrics.banned_patterns_found.length} found`
                  : "clean"
              }
            />
            {metrics.compliance_result && (
              <QualitySignal
                label="ACCME Compliance"
                passed={(metrics.compliance_result as Record<string, unknown>).passed as boolean}
              />
            )}
          </div>
        </div>

        {/* Recommendation */}
        <div>
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Shield className="h-3 w-3" />
            Recommendation
          </div>
          <p className="text-sm text-foreground">{recommendation.reasoning}</p>
        </div>

        {/* Banned patterns detail */}
        {metrics.banned_patterns_found && metrics.banned_patterns_found.length > 0 && (
          <div className="rounded-md bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 px-3 py-2">
            <p className="text-xs font-medium text-red-700 dark:text-red-300 mb-1">
              Banned patterns found:
            </p>
            <ul className="text-xs text-red-600 dark:text-red-400 space-y-0.5">
              {metrics.banned_patterns_found.map((pattern) => (
                <li key={pattern} className="font-mono">{pattern}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
