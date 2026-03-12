"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LEARNING_FORMATS } from "./cme-options";
import type { SectionC } from "@/types/cme";

interface Props {
  data: SectionC;
  onChange: (data: SectionC) => void;
}

export function SectionCEducational({ data, onChange }: Props) {
  function update(partial: Partial<SectionC>) {
    onChange({ ...data, ...partial });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">C. Educational Design</h3>

      <div className="space-y-2">
        <Label>Learning Format</Label>
        <Select value={data.learning_format} onValueChange={(v) => update({ learning_format: v as string })}>
          <SelectTrigger>
            <SelectValue placeholder="Select format" />
          </SelectTrigger>
          <SelectContent>
            {LEARNING_FORMATS.map((f) => (
              <SelectItem key={f} value={f}>{f}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="duration">Duration (minutes)</Label>
          <Input
            id="duration"
            type="number"
            value={data.duration_minutes ?? ""}
            onChange={(e) => update({ duration_minutes: e.target.value ? Number(e.target.value) : undefined })}
            placeholder="e.g., 60"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="faculty">Faculty Count</Label>
          <Input
            id="faculty"
            type="number"
            value={data.faculty_count ?? ""}
            onChange={(e) => update({ faculty_count: e.target.value ? Number(e.target.value) : undefined })}
            placeholder="e.g., 3"
          />
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label htmlFor="pre_test">Include Pre-Test</Label>
          <Switch id="pre_test" checked={data.include_pre_test} onCheckedChange={(v) => update({ include_pre_test: v })} />
        </div>
        <div className="flex items-center justify-between">
          <Label htmlFor="post_test">Include Post-Test</Label>
          <Switch id="post_test" checked={data.include_post_test} onCheckedChange={(v) => update({ include_post_test: v })} />
        </div>
      </div>
    </div>
  );
}
