"use client";

import { Check, Circle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type StepStatus = "completed" | "active" | "pending" | "error";

interface PipelineStepProps {
  label: string;
  status: StepStatus;
  selected: boolean;
  onClick: () => void;
}

export function PipelineStep({ label, status, selected, onClick }: PipelineStepProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 w-full text-left px-3 py-2 rounded-md text-xs transition-colors",
        selected
          ? "bg-primary/10 text-primary font-medium"
          : "text-foreground hover:bg-muted",
      )}
    >
      {status === "completed" && <Check className="h-3.5 w-3.5 shrink-0 text-primary" />}
      {status === "active" && <Loader2 className="h-3.5 w-3.5 shrink-0 text-dhg-orange animate-spin" />}
      {status === "pending" && <Circle className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
      {status === "error" && <Circle className="h-3.5 w-3.5 shrink-0 text-destructive" />}
      <span className="truncate">{label}</span>
    </button>
  );
}
