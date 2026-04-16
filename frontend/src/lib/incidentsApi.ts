const BASE = "/api/registry/api/incidents";

// ── Types ───────────────────────────────────────────────────────────────

export type Severity = "critical" | "high" | "medium" | "low";
export type IncidentStatus = "active" | "mitigated" | "resolved" | "postmortem";

export interface IncidentListItem {
  id: string;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  category: string;
  trigger_rule: string | null;
  affected_services: string[];
  parent_incident_id: string | null;
  detected_at: string;
  mitigated_at: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface IncidentEvent {
  id: string;
  incident_id: string;
  timestamp: string;
  event_type: string;
  source: string | null;
  description: string;
  evidence: Record<string, unknown> | null;
  created_at: string;
}

export interface IncidentAction {
  id: string;
  incident_id: string;
  action_type: string;
  description: string;
  command: string | null;
  result: string | null;
  performed_at: string;
  performed_by: string | null;
  created_at: string;
}

export interface Postmortem {
  id: string;
  incident_id: string;
  summary: string | null;
  timeline_markdown: string | null;
  root_cause_analysis: string | null;
  impact_analysis: string | null;
  resolution_details: string | null;
  prevention_measures: string | null;
  lessons_learned: string | null;
  sla_metrics: Record<string, unknown> | null;
  generated_at: string;
  last_edited_at: string | null;
  edited_by: string | null;
  created_at: string;
}

export interface IncidentDetail {
  id: string;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  category: string;
  root_cause: string | null;
  root_cause_category: string | null;
  impact_summary: string | null;
  prevention: string | null;
  trigger_rule: string | null;
  affected_services: string[];
  affected_project_ids: string[] | null;
  tags: string[];
  parent_incident_id: string | null;
  pipeline_run_id: string | null;
  system_snapshot: Record<string, unknown> | null;
  created_by: string | null;
  started_at: string | null;
  detected_at: string;
  mitigated_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
  events: IncidentEvent[] | null;
  actions: IncidentAction[] | null;
  postmortem: Postmortem | null;
  children: IncidentListItem[] | null;
}

export interface IncidentStats {
  total: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  avg_ttd_minutes: number | null;
  avg_ttm_minutes: number | null;
  avg_ttr_minutes: number | null;
  top_triggers: { trigger_rule: string; count: number }[];
}

export interface Runbook {
  id: string;
  trigger_rule: string;
  title: string;
  description: string | null;
  severity: string;
  remediation_mode: string;
  steps: Record<string, unknown>[];
  container_allowlist: string[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

// ── Fetch helper ────────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(
      `Incidents API ${res.status} ${res.statusText}${body ? `: ${body.slice(0, 200)}` : ""}`,
    );
  }
  return (await res.json()) as T;
}

// ── API functions ───────────────────────────────────────────────────────

export async function listIncidents(params: {
  status?: string;
  severity?: string;
  category?: string;
  service?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<IncidentListItem[]> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.severity) qs.set("severity", params.severity);
  if (params.category) qs.set("category", params.category);
  if (params.service) qs.set("service", params.service);
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.offset) qs.set("offset", String(params.offset));
  const q = qs.toString();
  return request<IncidentListItem[]>(q ? `?${q}` : "");
}

export async function getIncident(id: string): Promise<IncidentDetail> {
  return request<IncidentDetail>(`/${id}`);
}

export async function getStats(days = 30): Promise<IncidentStats> {
  return request<IncidentStats>(`/stats?days=${days}`);
}

export async function updateIncident(
  id: string,
  body: Record<string, unknown>,
): Promise<IncidentDetail> {
  return request<IncidentDetail>(`/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function addEvent(
  incidentId: string,
  body: { event_type: string; description: string; source?: string },
): Promise<IncidentEvent> {
  return request<IncidentEvent>(`/${incidentId}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function createPostmortem(
  incidentId: string,
  body: Record<string, unknown>,
): Promise<Postmortem> {
  return request<Postmortem>(`/${incidentId}/postmortem`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function listRunbooks(): Promise<Runbook[]> {
  return request<Runbook[]>("/runbooks");
}

// ── Severity helpers ────────────────────────────────────────────────────

export const SEVERITY_COLORS: Record<Severity, string> = {
  critical: "bg-red-600 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-500 text-black",
  low: "bg-blue-500 text-white",
};

export const STATUS_COLORS: Record<IncidentStatus, string> = {
  active: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  mitigated: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  resolved: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  postmortem: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
};
