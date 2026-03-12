"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MultiSelect } from "./multi-select";
import { TagInput } from "./tag-input";
import { GAP_EVIDENCE_SOURCES } from "./cme-options";
import type { SectionE } from "@/types/cme";

interface Props {
  data: SectionE;
  onChange: (data: SectionE) => void;
}

const GAP_PRIORITIES = [
  { value: "high", label: "High — Critical gap affecting patient outcomes" },
  { value: "medium", label: "Medium — Significant gap in knowledge or practice" },
  { value: "low", label: "Low — Incremental improvement opportunity" },
];

export function SectionEGaps({ data, onChange }: Props) {
  function update(partial: Partial<SectionE>) {
    onChange({ ...data, ...partial });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">E. Educational Gaps</h3>

      <div className="space-y-2">
        <Label>Knowledge Gaps</Label>
        <TagInput
          value={data.knowledge_gaps ?? []}
          onChange={(v) => update({ knowledge_gaps: v.length > 0 ? v : undefined })}
          placeholder="e.g., Lack of awareness of new treatment guidelines"
        />
        <p className="text-[10px] text-muted-foreground">What learners don&apos;t know</p>
      </div>

      <div className="space-y-2">
        <Label>Competence Gaps</Label>
        <TagInput
          value={data.competence_gaps ?? []}
          onChange={(v) => update({ competence_gaps: v.length > 0 ? v : undefined })}
          placeholder="e.g., Inability to apply risk stratification tools"
        />
        <p className="text-[10px] text-muted-foreground">What learners can&apos;t do (skills)</p>
      </div>

      <div className="space-y-2">
        <Label>Performance Gaps</Label>
        <TagInput
          value={data.performance_gaps ?? []}
          onChange={(v) => update({ performance_gaps: v.length > 0 ? v : undefined })}
          placeholder="e.g., Suboptimal prescribing patterns for guideline-directed therapy"
        />
        <p className="text-[10px] text-muted-foreground">What learners aren&apos;t doing in practice</p>
      </div>

      <div className="space-y-2">
        <Label>Gap Evidence Sources</Label>
        <MultiSelect
          options={GAP_EVIDENCE_SOURCES}
          value={data.gap_evidence_sources ?? []}
          onChange={(v) => update({ gap_evidence_sources: v.length > 0 ? v : undefined })}
          placeholder="Select evidence sources..."
        />
      </div>

      <div className="space-y-2">
        <Label>Gap Priority</Label>
        <Select value={data.gap_priority ?? undefined} onValueChange={(v) => update({ gap_priority: v as string || undefined })}>
          <SelectTrigger>
            <SelectValue placeholder="Select priority level" />
          </SelectTrigger>
          <SelectContent>
            {GAP_PRIORITIES.map((p) => (
              <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
