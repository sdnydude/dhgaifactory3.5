"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MultiSelect } from "./multi-select";
import { TagInput } from "./tag-input";
import {
  TREATMENT_MODALITIES,
  PATIENT_POPULATIONS,
  DISEASE_STAGES,
  COMMON_COMORBIDITIES,
} from "./cme-options";
import type { SectionD } from "@/types/cme";

interface Props {
  data: SectionD;
  onChange: (data: SectionD) => void;
}

export function SectionDClinical({ data, onChange }: Props) {
  function update(partial: Partial<SectionD>) {
    onChange({ ...data, ...partial });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">D. Clinical Focus</h3>

      <div className="space-y-2">
        <Label>Clinical Topics</Label>
        <TagInput
          value={data.clinical_topics}
          onChange={(v) => update({ clinical_topics: v })}
          placeholder="e.g., SGLT2 Inhibitors, GLP-1 Receptor Agonists"
        />
        <p className="text-[10px] text-muted-foreground">Free-text: specific to your disease state</p>
      </div>

      <div className="space-y-2">
        <Label>Treatment Modalities</Label>
        <MultiSelect
          options={TREATMENT_MODALITIES}
          value={data.treatment_modalities ?? []}
          onChange={(v) => update({ treatment_modalities: v.length > 0 ? v : undefined })}
          placeholder="Select modalities..."
        />
      </div>

      <div className="space-y-2">
        <Label>Patient Population</Label>
        <Select
          value={data.patient_population ?? undefined}
          onValueChange={(v) => update({ patient_population: v as string })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select population" />
          </SelectTrigger>
          <SelectContent>
            {PATIENT_POPULATIONS.map((p) => (
              <SelectItem key={p} value={p}>{p}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Stage of Disease</Label>
        <Select
          value={data.stage_of_disease ?? undefined}
          onValueChange={(v) => update({ stage_of_disease: v as string })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select stage" />
          </SelectTrigger>
          <SelectContent>
            {DISEASE_STAGES.map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Comorbidities</Label>
        <MultiSelect
          options={COMMON_COMORBIDITIES}
          value={data.comorbidities ?? []}
          onChange={(v) => update({ comorbidities: v.length > 0 ? v : undefined })}
          placeholder="Select comorbidities..."
        />
      </div>
    </div>
  );
}
