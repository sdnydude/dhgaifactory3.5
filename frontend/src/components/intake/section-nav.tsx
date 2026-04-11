"use client";

import { cn } from "@/lib/utils";
import { Check, Sparkles, X } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import type { PrefillConfidence } from "@/types/cme";

export interface SectionDef {
  id: string;
  label: string;
  required: boolean;
}

export const SECTIONS: SectionDef[] = [
  { id: "a", label: "A. Project Basics", required: true },
  { id: "b", label: "B. Supporter", required: false },
  { id: "c", label: "C. Educational Design", required: false },
  { id: "d", label: "D. Clinical Focus", required: false },
  { id: "e", label: "E. Educational Gaps", required: false },
  { id: "f", label: "F. Outcomes", required: false },
  { id: "g", label: "G. Content", required: false },
  { id: "h", label: "H. Logistics", required: false },
  { id: "i", label: "I. Compliance", required: false },
  { id: "j", label: "J. Additional", required: false },
];

type PrefillSectionStatus = "prefilled" | "accepted" | "cleared";

interface SectionNavProps {
  activeSection: string;
  onSelect: (id: string) => void;
  completedSections: Set<string>;
  prefillStatus?: Record<string, PrefillSectionStatus>;
  prefillConfidence?: Record<string, PrefillConfidence>;
  onAcceptSection?: (id: string) => void;
  onClearSection?: (id: string) => void;
}

const CONFIDENCE_DISPLAY: Record<PrefillConfidence, { letter: string; className: string; label: string }> = {
  high: { letter: "H", className: "text-green-500", label: "High confidence" },
  medium: { letter: "M", className: "text-amber-500", label: "Medium confidence" },
  low: { letter: "L", className: "text-destructive", label: "Low confidence" },
};

export function SectionNav({
  activeSection,
  onSelect,
  completedSections,
  prefillStatus = {},
  prefillConfidence = {},
  onAcceptSection,
  onClearSection,
}: SectionNavProps) {
  const progress = Math.round((completedSections.size / SECTIONS.length) * 100);

  return (
    <div className="w-[180px] shrink-0 border-r border-border p-4 space-y-3">
      <div className="space-y-1">
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <Progress value={progress} className="h-1.5" />
      </div>
      <nav className="space-y-0.5">
        {SECTIONS.map((section) => {
          const status = prefillStatus[section.id];
          const confidence = prefillConfidence[`section_${section.id}`];
          const isPrefilled = status === "prefilled";
          const confidenceInfo = confidence ? CONFIDENCE_DISPLAY[confidence] : null;

          return (
            <div key={section.id}>
              <button
                type="button"
                onClick={() => onSelect(section.id)}
                className={cn(
                  "flex items-center gap-2 w-full text-left px-2 py-1.5 rounded-md text-xs transition-colors",
                  activeSection === section.id
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground hover:bg-muted",
                )}
              >
                {completedSections.has(section.id) ? (
                  <Check className="h-3 w-3 shrink-0 text-green-500" />
                ) : isPrefilled ? (
                  <Sparkles className="h-3 w-3 shrink-0 text-primary" aria-hidden="true" />
                ) : (
                  <span className="h-3 w-3 shrink-0 rounded-full border border-border" />
                )}
                <span className="truncate">{section.label}</span>
                {section.required && (
                  <span className="text-[8px] text-destructive ml-auto" aria-label="Required">*</span>
                )}
                {isPrefilled && confidenceInfo && (
                  <span
                    className={cn("text-[10px] font-semibold ml-auto", confidenceInfo.className)}
                    title={confidenceInfo.label}
                    aria-label={confidenceInfo.label}
                  >
                    {confidenceInfo.letter}
                  </span>
                )}
              </button>

              {isPrefilled && (
                <div className="flex items-center gap-1.5 pl-7 py-0.5">
                  <span className="text-[10px] text-primary font-medium">AI Draft</span>
                  {onAcceptSection && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onAcceptSection(section.id);
                      }}
                      className="text-[10px] text-green-500 hover:underline ml-auto min-h-6 flex items-center"
                      aria-label={`Accept AI draft for ${section.label}`}
                    >
                      Accept
                    </button>
                  )}
                  {onClearSection && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onClearSection(section.id);
                      }}
                      className="text-muted-foreground hover:text-destructive min-h-6 min-w-6 flex items-center justify-center"
                      aria-label={`Clear AI draft for ${section.label}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </div>
  );
}
