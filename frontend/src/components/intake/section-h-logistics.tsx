"use client";

import { Label } from "@/components/ui/label";
import { DatePicker } from "./date-picker";
import { MultiSelect } from "./multi-select";
import { DISTRIBUTION_CHANNELS, GEO_REGIONS, LANGUAGES } from "./cme-options";
import type { SectionH } from "@/types/cme";

interface Props {
  data: SectionH;
  onChange: (data: SectionH) => void;
}

export function SectionHLogistics({ data, onChange }: Props) {
  function update(partial: Partial<SectionH>) {
    onChange({ ...data, ...partial });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">H. Logistics</h3>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Target Launch Date</Label>
          <DatePicker
            value={data.target_launch_date}
            onChange={(v) => update({ target_launch_date: v })}
          />
        </div>
        <div className="space-y-2">
          <Label>Expiration Date</Label>
          <DatePicker
            value={data.expiration_date}
            onChange={(v) => update({ expiration_date: v })}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Distribution Channels</Label>
        <MultiSelect
          options={DISTRIBUTION_CHANNELS}
          value={data.distribution_channels ?? []}
          onChange={(v) => update({ distribution_channels: v.length > 0 ? v : undefined })}
          placeholder="Select distribution channels..."
        />
      </div>

      <div className="space-y-2">
        <Label>Geographic Restrictions</Label>
        <MultiSelect
          options={GEO_REGIONS}
          value={data.geo_restrictions ?? []}
          onChange={(v) => update({ geo_restrictions: v.length > 0 ? v : undefined })}
          placeholder="Select regions..."
        />
      </div>

      <div className="space-y-2">
        <Label>Language Requirements</Label>
        <MultiSelect
          options={LANGUAGES}
          value={data.language_requirements ?? []}
          onChange={(v) => update({ language_requirements: v.length > 0 ? v : undefined })}
          placeholder="Select languages..."
        />
      </div>
    </div>
  );
}
