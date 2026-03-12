"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { DatePicker } from "./date-picker";
import type { SectionB } from "@/types/cme";

interface Props {
  data: SectionB;
  onChange: (data: SectionB) => void;
}

export function SectionBSupporter({ data, onChange }: Props) {
  function update(partial: Partial<SectionB>) {
    onChange({ ...data, ...partial });
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold">B. Supporter Information</h3>

      <div className="space-y-2">
        <Label htmlFor="supporter_name">Supporter Name</Label>
        <Input
          id="supporter_name"
          value={data.supporter_name}
          onChange={(e) => update({ supporter_name: e.target.value })}
          placeholder="e.g., Pfizer"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="supporter_contact_name">Contact Name</Label>
          <Input
            id="supporter_contact_name"
            value={data.supporter_contact_name ?? ""}
            onChange={(e) => update({ supporter_contact_name: e.target.value || undefined })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="supporter_contact_email">Contact Email</Label>
          <Input
            id="supporter_contact_email"
            type="email"
            value={data.supporter_contact_email ?? ""}
            onChange={(e) => update({ supporter_contact_email: e.target.value || undefined })}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="grant_amount">Grant Amount Requested ($)</Label>
        <Input
          id="grant_amount"
          type="number"
          value={data.grant_amount_requested ?? ""}
          onChange={(e) => update({ grant_amount_requested: e.target.value ? Number(e.target.value) : undefined })}
          placeholder="e.g., 250000"
        />
      </div>

      <div className="space-y-2">
        <Label>Grant Submission Deadline</Label>
        <DatePicker
          value={data.grant_submission_deadline}
          onChange={(v) => update({ grant_submission_deadline: v })}
        />
      </div>
    </div>
  );
}
