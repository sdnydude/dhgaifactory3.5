const BASE = "/api/registry/api/cme/export";

export interface ProjectListItem {
  id: string;
  name: string;
  status: string;
  kind: string | null;
  document_count: number;
  last_activity_at: string | null;
  drive_folder_id: string | null;
}

export interface ProjectListResponse {
  projects: ProjectListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProjectDocumentItem {
  id: string;
  document_type: string;
  title: string | null;
  word_count: number | null;
  version: number;
  is_current: boolean;
  created_at: string;
  drive_file_id: string | null;
}

export interface ProjectDocumentsResponse {
  project_id: string;
  documents: ProjectDocumentItem[];
}

export type BundleJobScope = "document" | "project_bundle" | "drive_sync";
export type BundleJobStatus = "pending" | "running" | "succeeded" | "failed";

export interface BundleJobResponse {
  id: string;
  project_id: string | null;
  scope: BundleJobScope;
  status: BundleJobStatus;
  selected_document_ids: string[] | null;
  created_at: string;
  completed_at: string | null;
  artifact_bytes: number | null;
  error: string | null;
}

export interface CreateBundleJobBody {
  project_id: string;
  document_ids: string[] | null;
  include_manifest: boolean;
  include_intake: boolean;
}

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
      `Files API ${res.status} ${res.statusText}${body ? `: ${body.slice(0, 200)}` : ""}`,
    );
  }
  return (await res.json()) as T;
}

export async function listProjects(params: {
  search?: string;
  status?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<ProjectListResponse> {
  const qs = new URLSearchParams();
  if (params.search) qs.set("search", params.search);
  if (params.status) qs.set("status", params.status);
  qs.set("limit", String(params.limit ?? 50));
  qs.set("offset", String(params.offset ?? 0));
  return request<ProjectListResponse>(`/projects?${qs.toString()}`);
}

export async function listProjectDocuments(
  projectId: string,
): Promise<ProjectDocumentsResponse> {
  return request<ProjectDocumentsResponse>(
    `/projects/${encodeURIComponent(projectId)}/documents`,
  );
}

export async function createBundleJob(
  body: CreateBundleJobBody,
): Promise<BundleJobResponse> {
  return request<BundleJobResponse>(`/bundle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getJob(jobId: string): Promise<BundleJobResponse> {
  return request<BundleJobResponse>(`/job/${encodeURIComponent(jobId)}`);
}

export async function listJobs(limit = 20): Promise<BundleJobResponse[]> {
  return request<BundleJobResponse[]>(`/jobs?limit=${limit}`);
}

export function artifactUrl(jobId: string): string {
  return `${BASE}/artifact/${encodeURIComponent(jobId)}`;
}
