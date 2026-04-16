"use client";

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { FileText } from "lucide-react";
import { useIncidentsStore } from "@/stores/incidents-store";
import type { IncidentDetail } from "@/lib/incidentsApi";

interface PostmortemFormProps {
  incident: IncidentDetail;
}

const FIELDS = [
  { key: "summary", label: "Summary", rows: 3 },
  { key: "root_cause_analysis", label: "Root Cause Analysis", rows: 4 },
  { key: "impact_analysis", label: "Impact Analysis", rows: 3 },
  { key: "resolution_details", label: "Resolution Details", rows: 3 },
  { key: "prevention_measures", label: "Prevention Measures", rows: 3 },
  { key: "lessons_learned", label: "Lessons Learned", rows: 3 },
] as const;

type FormData = Record<(typeof FIELDS)[number]["key"], string>;

function formatTs(ts: string | null): string {
  if (!ts) return "N/A";
  return new Date(ts).toLocaleString();
}

function buildPrefill(incident: IncidentDetail): FormData {
  // Summary: structured overview from incident metadata
  const svcList = incident.affected_services.length > 0
    ? incident.affected_services.join(", ")
    : "N/A";
  const summaryParts = [
    `${incident.severity.toUpperCase()} ${incident.category} incident: ${incident.title}`,
    `Affected services: ${svcList}`,
    `Detected: ${formatTs(incident.detected_at)}`,
    incident.mitigated_at ? `Mitigated: ${formatTs(incident.mitigated_at)}` : null,
    incident.resolved_at ? `Resolved: ${formatTs(incident.resolved_at)}` : null,
  ].filter(Boolean);

  // Root cause: direct from incident fields
  const rcParts: string[] = [];
  if (incident.root_cause_category) {
    rcParts.push(`Category: ${incident.root_cause_category}`);
  }
  if (incident.root_cause) {
    rcParts.push(incident.root_cause);
  }

  // Resolution details: built from actions log
  const actions = incident.actions ?? [];
  const resolutionActions = actions.filter(
    (a) => a.action_type !== "diagnostic",
  );
  const resParts = resolutionActions.map(
    (a) =>
      `- [${a.action_type}] ${a.description}${a.result ? ` — Result: ${a.result}` : ""}`,
  );

  return {
    summary: summaryParts.join("\n"),
    root_cause_analysis: rcParts.join("\n\n") || "",
    impact_analysis: incident.impact_summary ?? "",
    resolution_details: resParts.length > 0
      ? resParts.join("\n")
      : "",
    prevention_measures: incident.prevention ?? "",
    lessons_learned: "",
  };
}

export function PostmortemForm({ incident }: PostmortemFormProps) {
  const prefill = useMemo(() => buildPrefill(incident), [incident]);
  const [form, setForm] = useState<FormData>(prefill);
  const [expanded, setExpanded] = useState(false);
  const actionLoading = useIncidentsStore((s) => s.actionLoading);
  const submitPostmortem = useIncidentsStore((s) => s.createPostmortem);

  const hasContent = Object.values(form).some((v) => v.trim().length > 0);

  const handleSubmit = async () => {
    const body: Record<string, string> = {};
    for (const [k, v] of Object.entries(form)) {
      if (v.trim()) body[k] = v.trim();
    }
    if (Object.keys(body).length === 0) return;
    await submitPostmortem(incident.id, body);
    setExpanded(false);
  };

  if (!expanded) {
    return (
      <div className="rounded-lg border border-dashed border-purple-400/50 bg-purple-50/30 dark:bg-purple-900/10 p-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setExpanded(true)}
          className="w-full text-xs border-purple-300 hover:bg-purple-100 dark:border-purple-700 dark:hover:bg-purple-900/30"
        >
          <FileText className="h-3.5 w-3.5 mr-1.5" />
          Create Post-Mortem
        </Button>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-purple-400/50 bg-card p-4 space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400">
        New Post-Mortem
      </h3>

      {FIELDS.map(({ key, label, rows }) => (
        <div key={key}>
          <label
            htmlFor={`pm-${key}`}
            className="block text-[11px] font-medium text-muted-foreground mb-1"
          >
            {label}
          </label>
          <textarea
            id={`pm-${key}`}
            rows={rows}
            value={form[key]}
            onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-purple-500 resize-y"
            placeholder={`Enter ${label.toLowerCase()}...`}
          />
        </div>
      ))}

      <div className="flex items-center gap-2 pt-1">
        <Button
          size="sm"
          disabled={!hasContent || actionLoading}
          onClick={handleSubmit}
          className="text-xs bg-purple-600 hover:bg-purple-700"
        >
          <FileText className="h-3.5 w-3.5 mr-1.5" />
          {actionLoading ? "Submitting..." : "Submit Post-Mortem"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={actionLoading}
          onClick={() => {
            setForm(prefill);
            setExpanded(false);
          }}
          className="text-xs"
        >
          Cancel
        </Button>
      </div>
    </div>
  );
}
