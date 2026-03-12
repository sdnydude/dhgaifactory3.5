"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MultiSelect } from "./multi-select";
import { Checkbox } from "@/components/ui/checkbox";
import { MEASUREMENT_APPROACHES, FOLLOW_UP_TIMELINES } from "./cme-options";
import type { SectionF } from "@/types/cme";

interface Props {
  data: SectionF;
  onChange: (data: SectionF) => void;
}

const MOORE_LEVELS = [
  { level: 1, label: "Level 1 — Participation" },
  { level: 2, label: "Level 2 — Satisfaction" },
  { level: 3, label: "Level 3A — Declarative Knowledge" },
  { level: 3.5, label: "Level 3B — Procedural Knowledge" },
  { level: 4, label: "Level 4 — Competence" },
  { level: 5, label: "Level 5 — Performance" },
  { level: 6, label: "Level 6 — Patient Health" },
  { level: 7, label: "Level 7 — Community Health" },
];

export function SectionFOutcomes({ data, onChange }: Props) {
  function update(partial: Partial<SectionF>) {
    onChange({ ...data, ...partial });
  }

  function toggleMooreLevel(level: number) {
    const current = data.moore_levels_target ?? [];
    const next = current.includes(level)
      ? current.filter((l) => l !== level)
      : [...current, level];
    update({ moore_levels_target: next.length > 0 ? next : undefined });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">F. Outcomes & Measurement</h3>

      <div className="space-y-2">
        <Label>Primary Outcomes</Label>
        <MultiSelect
          options={MEASUREMENT_APPROACHES}
          value={data.primary_outcomes ?? []}
          onChange={(v) => update({ primary_outcomes: v.length > 0 ? v : undefined })}
          placeholder="Select primary outcome measures..."
        />
      </div>

      <div className="space-y-2">
        <Label>Secondary Outcomes</Label>
        <MultiSelect
          options={MEASUREMENT_APPROACHES}
          value={data.secondary_outcomes ?? []}
          onChange={(v) => update({ secondary_outcomes: v.length > 0 ? v : undefined })}
          placeholder="Select secondary outcome measures..."
        />
      </div>

      <div className="space-y-2">
        <Label>Measurement Approach</Label>
        <Select
          value={data.measurement_approach ?? undefined}
          onValueChange={(v) => update({ measurement_approach: v as string })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select measurement approach" />
          </SelectTrigger>
          <SelectContent>
            {MEASUREMENT_APPROACHES.map((m) => (
              <SelectItem key={m} value={m}>{m}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Moore&apos;s Expanded Framework Target Levels</Label>
        <div className="space-y-2 rounded-md border border-border p-3">
          {MOORE_LEVELS.map((m) => (
            <label key={m.level} className="flex items-center gap-2.5 text-sm cursor-pointer">
              <Checkbox
                checked={(data.moore_levels_target ?? []).includes(m.level)}
                onCheckedChange={() => toggleMooreLevel(m.level)}
              />
              <span>{m.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label>Follow-up Timeline</Label>
        <Select
          value={data.follow_up_timeline ?? undefined}
          onValueChange={(v) => update({ follow_up_timeline: v as string })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select follow-up timeline" />
          </SelectTrigger>
          <SelectContent>
            {FOLLOW_UP_TIMELINES.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
