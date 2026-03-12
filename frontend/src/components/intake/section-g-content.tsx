"use client";

import { Label } from "@/components/ui/label";
import { MultiSelect } from "./multi-select";
import { TagInput } from "./tag-input";
import { REGULATORY_CONSIDERATIONS } from "./cme-options";
import type { SectionG } from "@/types/cme";

interface Props {
  data: SectionG;
  onChange: (data: SectionG) => void;
}

export function SectionGContent({ data, onChange }: Props) {
  function update(partial: Partial<SectionG>) {
    onChange({ ...data, ...partial });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">G. Content Requirements</h3>

      <div className="space-y-2">
        <Label>Key Messages</Label>
        <TagInput
          value={data.key_messages ?? []}
          onChange={(v) => update({ key_messages: v.length > 0 ? v : undefined })}
          placeholder="e.g., Early intervention improves long-term outcomes"
        />
        <p className="text-[10px] text-muted-foreground">Core messages the educational activity must convey</p>
      </div>

      <div className="space-y-2">
        <Label>Required References</Label>
        <TagInput
          value={data.required_references ?? []}
          onChange={(v) => update({ required_references: v.length > 0 ? v : undefined })}
          placeholder="e.g., AHA/ACC 2024 Heart Failure Guidelines"
        />
        <p className="text-[10px] text-muted-foreground">Specific guidelines, trials, or publications that must be cited</p>
      </div>

      <div className="space-y-2">
        <Label>Excluded Topics</Label>
        <TagInput
          value={data.excluded_topics ?? []}
          onChange={(v) => update({ excluded_topics: v.length > 0 ? v : undefined })}
          placeholder="e.g., Head-to-head branded drug comparisons"
        />
        <p className="text-[10px] text-muted-foreground">Topics or comparisons to avoid</p>
      </div>

      <div className="space-y-2">
        <Label>Competitor Products to Mention</Label>
        <TagInput
          value={data.competitor_products_to_mention ?? []}
          onChange={(v) => update({ competitor_products_to_mention: v.length > 0 ? v : undefined })}
          placeholder="e.g., Drug class comparisons (SGLT2i, GLP-1 RA)"
        />
      </div>

      <div className="space-y-2">
        <Label>Regulatory Considerations</Label>
        <MultiSelect
          options={REGULATORY_CONSIDERATIONS}
          value={data.regulatory_considerations ? [data.regulatory_considerations] : []}
          onChange={(v) => update({ regulatory_considerations: v[0] || undefined })}
          placeholder="Select regulatory considerations..."
          maxSelections={1}
        />
      </div>
    </div>
  );
}
