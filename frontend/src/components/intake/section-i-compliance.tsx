"use client";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import type { SectionI } from "@/types/cme";

interface Props {
  data: SectionI;
  onChange: (data: SectionI) => void;
}

export function SectionICompliance({ data, onChange }: Props) {
  function update(partial: Partial<SectionI>) {
    onChange({ ...data, ...partial });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">I. Compliance & Disclosure</h3>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label htmlFor="accme">ACCME Compliant</Label>
          <Switch id="accme" checked={data.accme_compliant} onCheckedChange={(v) => update({ accme_compliant: v })} />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="financial">Financial Disclosure Required</Label>
          <Switch id="financial" checked={data.financial_disclosure_required} onCheckedChange={(v) => update({ financial_disclosure_required: v })} />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="offlabel">Off-Label Discussion</Label>
          <Switch id="offlabel" checked={data.off_label_discussion} onCheckedChange={(v) => update({ off_label_discussion: v })} />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="commercial">Commercial Support Acknowledgment</Label>
          <Switch id="commercial" checked={data.commercial_support_acknowledgment} onCheckedChange={(v) => update({ commercial_support_acknowledgment: v })} />
        </div>
      </div>
    </div>
  );
}
