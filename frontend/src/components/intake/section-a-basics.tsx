"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { MultiSelect } from "./multi-select";
import { TARGET_AUDIENCES, HCP_CREDENTIAL_TYPES, THERAPEUTIC_AREAS, DISEASE_STATES } from "./cme-options";
import type { SectionA } from "@/types/cme";

const DISEASE_STATE_VALUES = DISEASE_STATES.map((d) => d.value);
const DISEASE_TIER_MAP = new Map(DISEASE_STATES.map((d) => [d.value, d.tier]));
const TIER_STYLES = {
  high: "text-green-600 dark:text-green-400",
  medium: "text-amber-600 dark:text-amber-400",
  low: "text-zinc-400 dark:text-zinc-500",
} as const;

function renderDiseaseLabel(option: string) {
  const tier = DISEASE_TIER_MAP.get(option);
  if (!tier) return option;
  const letter = tier === "high" ? "H" : tier === "medium" ? "M" : "L";
  return (
    <span>
      <span className={`text-xs font-medium mr-1.5 ${TIER_STYLES[tier]}`}>{letter}</span>
      {option}
    </span>
  );
}

interface Props {
  data: SectionA;
  onChange: (data: SectionA) => void;
}

export function SectionABasics({ data, onChange }: Props) {
  function update(partial: Partial<SectionA>) {
    onChange({ ...data, ...partial });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">A. Project Basics</h3>

      <div className="space-y-2">
        <Label htmlFor="project_name">Project Name *</Label>
        <Input
          id="project_name"
          value={data.project_name}
          onChange={(e) => update({ project_name: e.target.value })}
          placeholder="e.g., Advances in Heart Failure Management"
          maxLength={200}
        />
        <p className="text-[10px] text-muted-foreground">5-200 characters</p>
      </div>

      <div className="space-y-2">
        <Label>Therapeutic Area *</Label>
        <MultiSelect
          options={THERAPEUTIC_AREAS}
          value={data.therapeutic_area}
          onChange={(v) => update({ therapeutic_area: v })}
          placeholder="Select therapeutic areas..."
          maxSelections={5}
        />
      </div>

      <div className="space-y-2">
        <Label>Disease State *</Label>
        <MultiSelect
          options={DISEASE_STATE_VALUES}
          value={data.disease_state}
          onChange={(v) => update({ disease_state: v })}
          placeholder="Select disease states..."
          maxSelections={10}
          renderLabel={renderDiseaseLabel}
        />
        <p className="text-[10px] text-muted-foreground">H/M/L = funding likelihood based on pharma commercial support activity</p>
      </div>

      <div className="space-y-2">
        <Label>Primary Target Audience * (1-5)</Label>
        <MultiSelect
          options={TARGET_AUDIENCES}
          value={data.target_audience_primary}
          onChange={(v) => update({ target_audience_primary: v })}
          placeholder="Select target audience..."
          maxSelections={5}
        />
      </div>

      <div className="space-y-2">
        <Label>Secondary Target Audience (up to 3)</Label>
        <MultiSelect
          options={TARGET_AUDIENCES}
          value={data.target_audience_secondary ?? []}
          onChange={(v) => update({ target_audience_secondary: v.length > 0 ? v : undefined })}
          placeholder="Select secondary audience..."
          maxSelections={3}
        />
      </div>

      <div className="space-y-2">
        <Label>HCP Credential Types</Label>
        <MultiSelect
          options={HCP_CREDENTIAL_TYPES}
          value={data.target_hcp_types ?? []}
          onChange={(v) => update({ target_hcp_types: v.length > 0 ? v : undefined })}
          placeholder="Select credential types..."
        />
        <p className="text-[10px] text-muted-foreground">Professional designations eligible for this activity</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="additional_context">Additional Context</Label>
        <Textarea
          id="additional_context"
          value={data.additional_context ?? ""}
          onChange={(e) => update({ additional_context: e.target.value || undefined })}
          placeholder="Clinical hypotheses, focus areas, key treatments, strategic direction — anything that helps the AI generate better drafts"
          rows={4}
          maxLength={5000}
        />
        <p className="text-[10px] text-muted-foreground">Optional — helps the AI prefill produce more relevant drafts</p>
      </div>
    </div>
  );
}
