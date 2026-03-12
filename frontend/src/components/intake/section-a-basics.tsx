"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectSeparator, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MultiSelect } from "./multi-select";
import { TARGET_AUDIENCES, HCP_CREDENTIAL_TYPES, THERAPEUTIC_AREAS, DISEASE_STATES } from "./cme-options";
import type { SectionA } from "@/types/cme";

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
        <Select value={data.therapeutic_area} onValueChange={(v) => update({ therapeutic_area: v ?? "" })}>
          <SelectTrigger>
            <SelectValue placeholder="Select therapeutic area" />
          </SelectTrigger>
          <SelectContent>
            {THERAPEUTIC_AREAS.map((area) => (
              <SelectItem key={area} value={area}>
                {area}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Disease State *</Label>
        <Select value={data.disease_state} onValueChange={(v) => update({ disease_state: v ?? "" })}>
          <SelectTrigger>
            <SelectValue placeholder="Select disease state" />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectLabel>High Funding Likelihood</SelectLabel>
              {DISEASE_STATES.filter((d) => d.tier === "high").map((d) => (
                <SelectItem key={d.value} value={d.value}>
                  <span className="text-xs font-medium text-green-600 dark:text-green-400 mr-1.5">H</span>{d.value}
                </SelectItem>
              ))}
            </SelectGroup>
            <SelectSeparator />
            <SelectGroup>
              <SelectLabel>Medium Funding Likelihood</SelectLabel>
              {DISEASE_STATES.filter((d) => d.tier === "medium").map((d) => (
                <SelectItem key={d.value} value={d.value}>
                  <span className="text-xs font-medium text-amber-600 dark:text-amber-400 mr-1.5">M</span>{d.value}
                </SelectItem>
              ))}
            </SelectGroup>
            <SelectSeparator />
            <SelectGroup>
              <SelectLabel>Lower Funding Likelihood</SelectLabel>
              {DISEASE_STATES.filter((d) => d.tier === "low").map((d) => (
                <SelectItem key={d.value} value={d.value}>
                  <span className="text-xs font-medium text-zinc-400 dark:text-zinc-500 mr-1.5">L</span>{d.value}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
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
    </div>
  );
}
