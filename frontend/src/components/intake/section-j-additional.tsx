"use client";

import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { TagInput } from "./tag-input";
import type { SectionJ } from "@/types/cme";

interface Props {
  data: SectionJ;
  onChange: (data: SectionJ) => void;
}

export function SectionJAdditional({ data, onChange }: Props) {
  function update(partial: Partial<SectionJ>) {
    onChange({ ...data, ...partial });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">J. Additional Information</h3>

      <div className="space-y-2">
        <Label htmlFor="special">Special Instructions</Label>
        <Textarea
          id="special"
          value={data.special_instructions ?? ""}
          onChange={(e) => update({ special_instructions: e.target.value || undefined })}
          placeholder="Any special instructions for the AI agents..."
          rows={4}
        />
      </div>

      <div className="space-y-2">
        <Label>Reference Materials</Label>
        <TagInput
          value={data.reference_materials ?? []}
          onChange={(v) => update({ reference_materials: v })}
          placeholder="e.g., URL or document title"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="notes">Internal Notes</Label>
        <Textarea
          id="notes"
          value={data.internal_notes ?? ""}
          onChange={(e) => update({ internal_notes: e.target.value || undefined })}
          placeholder="Internal notes (not shared with agents)"
          rows={3}
        />
      </div>
    </div>
  );
}
