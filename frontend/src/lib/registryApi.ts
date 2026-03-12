import type {
  IntakeSubmission,
  CMEProjectCreateResponse,
  CMEProjectDetail,
  ExecutionStatus,
  AgentOutput,
  CMEProjectStatus,
} from "@/types/cme";

const BASE_URL =
  process.env.NEXT_PUBLIC_REGISTRY_API_URL || "http://localhost:8011";

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
    throw new Error(`Registry API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// =============================================================================
// PROJECT CRUD
// =============================================================================

export async function createProject(
  intake: IntakeSubmission,
): Promise<CMEProjectCreateResponse> {
  return apiFetch<CMEProjectCreateResponse>("/api/cme/projects", {
    method: "POST",
    body: JSON.stringify(intake),
  });
}

export async function listProjects(
  status?: CMEProjectStatus,
  skip = 0,
  limit = 100,
): Promise<CMEProjectDetail[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (skip) params.set("skip", String(skip));
  if (limit !== 100) params.set("limit", String(limit));
  const qs = params.toString();
  return apiFetch<CMEProjectDetail[]>(
    `/api/cme/projects${qs ? `?${qs}` : ""}`,
  );
}

export async function getProject(
  projectId: string,
): Promise<CMEProjectDetail> {
  return apiFetch<CMEProjectDetail>(`/api/cme/projects/${projectId}`);
}

// =============================================================================
// PIPELINE CONTROL
// =============================================================================

export async function startPipeline(
  projectId: string,
): Promise<ExecutionStatus> {
  return apiFetch<ExecutionStatus>(`/api/cme/projects/${projectId}/start`, {
    method: "POST",
  });
}

export async function getPipelineStatus(
  projectId: string,
): Promise<ExecutionStatus> {
  return apiFetch<ExecutionStatus>(`/api/cme/projects/${projectId}/status`);
}

export async function pausePipeline(
  projectId: string,
): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(
    `/api/cme/projects/${projectId}/pause`,
    { method: "POST" },
  );
}

export async function resumePipeline(
  projectId: string,
): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(
    `/api/cme/projects/${projectId}/resume`,
    { method: "POST" },
  );
}

export async function cancelPipeline(
  projectId: string,
): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(
    `/api/cme/projects/${projectId}/cancel`,
    { method: "POST" },
  );
}

// =============================================================================
// CLOUD SYNC (polls LangGraph Cloud for thread state)
// =============================================================================

export async function syncProjectFromCloud(
  projectId: string,
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/cme/projects/${projectId}/sync`,
    { method: "POST" },
  );
}

export async function syncAllActiveProjects(): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/cme/sync-active", {
    method: "POST",
  });
}

// =============================================================================
// AGENT OUTPUTS
// =============================================================================

export async function listOutputs(
  projectId: string,
): Promise<AgentOutput[]> {
  return apiFetch<AgentOutput[]>(`/api/cme/projects/${projectId}/outputs`);
}

export async function getAgentOutput(
  projectId: string,
  agentName: string,
): Promise<AgentOutput> {
  return apiFetch<AgentOutput>(
    `/api/cme/projects/${projectId}/outputs/${agentName}`,
  );
}

// =============================================================================
// REVIEWS
// =============================================================================

export async function submitForReview(
  projectId: string,
  reviewerEmails: string[],
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/cme/projects/${projectId}/submit-for-review`,
    { method: "POST", body: JSON.stringify({ reviewer_emails: reviewerEmails }) },
  );
}

export async function getReviewStatus(
  projectId: string,
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/cme/projects/${projectId}/review-status`,
  );
}

export async function submitReview(
  projectId: string,
  reviewerEmail: string,
  review: { decision: string; notes?: string; annotations?: unknown[] },
): Promise<Record<string, unknown>> {
  const params = new URLSearchParams({ reviewer_email: reviewerEmail });
  return apiFetch<Record<string, unknown>>(
    `/api/cme/projects/${projectId}/review?${params}`,
    { method: "POST", body: JSON.stringify(review) },
  );
}

export async function getMyReviews(): Promise<Record<string, unknown>[]> {
  return apiFetch<Record<string, unknown>[]>("/api/cme/my-reviews");
}
