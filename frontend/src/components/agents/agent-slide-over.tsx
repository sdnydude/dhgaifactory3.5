"use client";

import { ChevronDown, Play, ArrowLeft, ArrowRight } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { AgentCategory } from "@/lib/agent-catalog";
import { getCatalogEntry } from "@/lib/agent-catalog";
import type { AgentLibraryItem } from "./agents-library";

const CATEGORY_BADGE: Record<AgentCategory, string> = {
  content: "bg-[#663399]/10 text-[#663399] dark:text-[#a78bfa] border-[#663399]/30",
  recipe: "bg-[#F77E2D]/10 text-[#F77E2D] dark:text-[#fb923c] border-[#F77E2D]/30",
  qa: "bg-[#22c55e]/10 text-[#16a34a] dark:text-[#4ade80] border-[#22c55e]/30",
  infra: "bg-zinc-500/10 text-zinc-500 dark:text-zinc-400 border-zinc-500/30",
};

interface SlideOverProps {
  agent: AgentLibraryItem | null;
  onClose: () => void;
  onNavigate: (graphId: string) => void;
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
      <p className="text-lg font-semibold tabular-nums mt-0.5">{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
    </div>
  );
}

function DeepDocSection({ title, content }: { title: string; content: string }) {
  return (
    <Collapsible>
      <CollapsibleTrigger className="flex items-center justify-between w-full py-2 px-1 text-xs font-medium hover:text-foreground text-muted-foreground transition-colors group">
        {title}
        <ChevronDown className="h-3.5 w-3.5 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="px-1 pb-3">
          <pre className="text-[11px] text-muted-foreground whitespace-pre-wrap font-[Inter] leading-relaxed">
            {content}
          </pre>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function AgentSlideOver({ agent, onClose, onNavigate }: SlideOverProps) {
  if (!agent) return null;

  const catalogEntry = getCatalogEntry(agent.graphId);
  const deepDocs = catalogEntry?.deepDocs;

  const lastRunLabel = agent.lastRunAt
    ? new Date(agent.lastRunAt).toLocaleString()
    : "Never";

  return (
    <Sheet open={!!agent} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-[480px] sm:max-w-none overflow-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-3">
            <span className="text-2xl">{agent.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate">{agent.name}</span>
                <Badge variant="outline" className={`text-[10px] ${CATEGORY_BADGE[agent.category]}`}>
                  {agent.category}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground font-normal mt-0.5">{agent.description}</p>
            </div>
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6 px-6 pb-8">
          {/* 2x2 Stats Grid */}
          <div className="grid grid-cols-2 gap-3">
            <StatCard label="Total Runs" value={agent.totalRuns} />
            <StatCard label="Success Rate" value={`${agent.successRate}%`} />
            <StatCard label="Active" value={agent.running} />
            <StatCard label="Last Run" value={lastRunLabel} />
          </div>

          {/* Dependencies */}
          {(agent.upstream.length > 0 || agent.downstream.length > 0) && (
            <div className="space-y-2">
              <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Dependencies</h4>
              {agent.upstream.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <ArrowLeft className="h-3 w-3 text-muted-foreground shrink-0" />
                  <span className="text-[10px] text-muted-foreground w-14">Upstream:</span>
                  {agent.upstream.map((id) => (
                    <Badge
                      key={id}
                      variant="outline"
                      className="text-[10px] cursor-pointer hover:bg-muted transition-colors"
                      onClick={() => onNavigate(id)}
                    >
                      {id.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
              )}
              {agent.downstream.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                  <span className="text-[10px] text-muted-foreground w-14">Down:</span>
                  {agent.downstream.map((id) => (
                    <Badge
                      key={id}
                      variant="outline"
                      className="text-[10px] cursor-pointer hover:bg-muted transition-colors"
                      onClick={() => onNavigate(id)}
                    >
                      {id.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Inputs / Outputs tags */}
          <div className="space-y-2">
            <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Inputs</h4>
            <div className="flex flex-wrap gap-1">
              {agent.inputs.map((inp) => (
                <Badge key={inp} variant="secondary" className="text-[10px]">
                  {inp}
                </Badge>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Outputs</h4>
            <div className="flex flex-wrap gap-1">
              {agent.outputs.map((out) => (
                <Badge key={out} variant="secondary" className="text-[10px]">
                  {out}
                </Badge>
              ))}
            </div>
          </div>

          {/* Deep Docs */}
          {deepDocs && (
            <div className="space-y-1 border-t border-border pt-4">
              <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Documentation</h4>
              <DeepDocSection title="Execution Flow" content={deepDocs.executionFlow} />
              <DeepDocSection title="Quality Criteria" content={deepDocs.qualityCriteria} />
              <DeepDocSection title="Error Handling" content={deepDocs.errorHandling} />
              <DeepDocSection title="Input Schema" content={deepDocs.inputSchema} />
            </div>
          )}

          {/* Run Agent button (disabled) */}
          <div className="pt-4 border-t border-border">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button disabled className="w-full" variant="outline">
                    <Play className="h-4 w-4 mr-2" />
                    Run Agent
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  Agent execution is available through the pipeline recipes
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
