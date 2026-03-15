"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import type { VSDistribution, VSItem } from "./types";

interface VSAlternativesProps {
  distribution: VSDistribution;
  agentLabel: string;
  onSelect?: (item: VSItem, originalIndex: number) => void;
}

// DHG brand colors per spec Section 11.3 and .claude/rules/dhg-brand.md
const LABEL_STYLES: Record<string, string> = {
  conventional: "bg-dhg-purple/10 text-dhg-purple border-dhg-purple/20",
  novel: "bg-dhg-orange/10 text-dhg-orange border-dhg-orange/20",
  exploratory: "bg-dhg-graphite/10 text-dhg-graphite border-dhg-graphite/20",
};

function shuffleArray<T>(arr: T[], seed: number): T[] {
  const shuffled = [...arr];
  let s = seed;
  for (let i = shuffled.length - 1; i > 0; i--) {
    s = (s * 16807 + 0) % 2147483647;
    const j = s % (i + 1);
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export function VSAlternatives({ distribution, agentLabel, onSelect }: VSAlternativesProps) {
  const [expanded, setExpanded] = useState(false);

  if (!distribution || !distribution.items || distribution.items.length <= 1) {
    return null;
  }

  // Shuffle items to eliminate positional bias — use distribution_id as deterministic seed
  // Multiplicative hash (djb2-style) for better entropy than simple char code sum
  const seed = distribution.distribution_id
    .split("")
    .reduce((acc, c) => (acc * 31 + c.charCodeAt(0)) | 0, 0);
  const shuffledItems = shuffleArray(distribution.items, seed);

  return (
    <div className="mt-3 border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 bg-muted/30 hover:bg-muted/50 transition-colors text-sm"
      >
        <span className="flex items-center gap-2 text-muted-foreground">
          <Sparkles className="h-4 w-4 text-dhg-purple" />
          {distribution.items.length} VS alternatives for {agentLabel}
          {distribution.tau_relaxed && (
            <Badge variant="outline" className="text-xs">tau relaxed</Badge>
          )}
        </span>
        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {expanded && (
        <div className="p-3 space-y-2">
          {shuffledItems.map((item, idx) => {
            // The first item in the original (pre-shuffle) distribution is the auto-selected one
            const originalIndex = distribution.items.indexOf(item);
            const isAutoSelected = originalIndex === 0;
            return (
              <VSAlternativeCard
                key={idx}
                item={item}
                isAutoSelected={isAutoSelected}
                onClick={onSelect ? () => onSelect(item, originalIndex) : undefined}
              />
            );
          })}
          <div className="text-xs text-muted-foreground pt-1">
            Model: {distribution.model} · Phase: {distribution.phase} · k={distribution.k} · τ={distribution.tau}
          </div>
        </div>
      )}
    </div>
  );
}

function VSAlternativeCard({ item, isAutoSelected, onClick }: { item: VSItem; isAutoSelected: boolean; onClick?: () => void }) {
  const label = item.metadata?.label ?? "conventional";
  const labelStyle = LABEL_STYLES[label] ?? LABEL_STYLES.conventional;
  const confidencePct = (item.probability * 100).toFixed(0);

  return (
    <Card
      className={`border-border/50 ${isAutoSelected ? "border-l-2 border-l-dhg-purple" : ""} ${onClick ? "cursor-pointer hover:bg-muted/30 transition-colors" : ""}`}
      onClick={onClick}
    >
      <CardContent className="p-3">
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className={`text-xs ${labelStyle}`}>
                {label}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {confidencePct}% confidence
              </span>
              {isAutoSelected && (
                <span className="text-xs text-dhg-purple font-medium">auto-selected</span>
              )}
            </div>
            <p className="text-sm whitespace-pre-wrap">{item.content}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
