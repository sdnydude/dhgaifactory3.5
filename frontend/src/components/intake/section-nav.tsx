"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";
import { Progress } from "@/components/ui/progress";

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

interface SectionNavProps {
  activeSection: string;
  onSelect: (id: string) => void;
  completedSections: Set<string>;
}

export function SectionNav({ activeSection, onSelect, completedSections }: SectionNavProps) {
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
        {SECTIONS.map((section) => (
          <button
            key={section.id}
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
            ) : (
              <span className="h-3 w-3 shrink-0 rounded-full border border-border" />
            )}
            <span className="truncate">{section.label}</span>
            {section.required && (
              <span className="text-[8px] text-destructive ml-auto">*</span>
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}
