export type DevChangelogCategory =
  | "feature"
  | "infra"
  | "fix"
  | "refactor"
  | "docs"
  | "debt";

export type DevChangelogStatus =
  | "shipped"
  | "in_progress"
  | "backlog"
  | "abandoned";

export type DevChangelogSource = "manual" | "agent" | "mixed";

export interface DevChangelogCommit {
  sha: string;
  date: string;
  subject: string;
  author?: string;
}

export interface DevChangelogEntry {
  id: string;
  slug: string;
  epic: string;
  category: DevChangelogCategory;
  detected_status: DevChangelogStatus;
  declared_status: DevChangelogStatus | null;
  window_start: string;
  window_end: string | null;
  commit_count: number;
  commits: DevChangelogCommit[];
  sessions: Array<Record<string, unknown>>;
  key_insight: string | null;
  notes: string | null;
  priority: number | null;
  locked: boolean;
  source: DevChangelogSource;
  detected_at: string;
  last_agent_run_at: string | null;
  last_human_edit_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DevChangelogList {
  entries: DevChangelogEntry[];
  total: number;
}

export interface DevChangelogPatch {
  declared_status?: DevChangelogStatus | null;
  key_insight?: string | null;
  notes?: string | null;
  priority?: number | null;
  locked?: boolean;
}

export interface DevChangelogFilters {
  status?: DevChangelogStatus;
  category?: DevChangelogCategory;
  window_start?: string;
  window_end?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

const BASE_URL = "/api/registry";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Dev Changelog API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function listDevChangelog(
  filters: DevChangelogFilters = {},
): Promise<DevChangelogList> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.category) params.set("category", filters.category);
  if (filters.window_start) params.set("window_start", filters.window_start);
  if (filters.window_end) params.set("window_end", filters.window_end);
  if (filters.q) params.set("q", filters.q);
  if (filters.limit != null) params.set("limit", String(filters.limit));
  if (filters.offset != null) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return apiFetch<DevChangelogList>(
    `/api/dev-changelog${qs ? `?${qs}` : ""}`,
  );
}

export async function getDevChangelog(
  slug: string,
): Promise<DevChangelogEntry> {
  return apiFetch<DevChangelogEntry>(`/api/dev-changelog/${slug}`);
}

export async function patchDevChangelog(
  slug: string,
  patch: DevChangelogPatch,
): Promise<DevChangelogEntry> {
  return apiFetch<DevChangelogEntry>(`/api/dev-changelog/${slug}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}
