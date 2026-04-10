import { Client } from "@langchain/langgraph-sdk";

const createClient = () => {
  const envUrl = process.env.NEXT_PUBLIC_LANGGRAPH_API_URL ?? "/api/langgraph";
  const baseUrl = envUrl.startsWith("/")
    ? (typeof window !== "undefined" ? `${window.location.origin}${envUrl}` : `http://localhost:3000${envUrl}`)
    : envUrl;
  return new Client({ apiUrl: baseUrl });
};

export interface RunningAgent {
  threadId: string;
  runId: string;
  graphId: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  metadata: Record<string, unknown>;
  projectName: string;
}

export interface AssistantInfo {
  assistantId: string;
  graphId: string;
  name: string;
  createdAt: string;
}

export interface ThreadState {
  projectId: string;
  projectName: string;
  status: string;
  currentStep: string;
  errors: Array<Record<string, unknown>>;
  completedOutputs: string[];
  retryCount: number;
  lastCheckpoint: string;
  checkpointAgent: string;
  humanReviewStatus: string | null;
  reviewRound: number;
  outputContents: Record<string, string>;
  vsDistributions: Record<string, VsDistribution>;
  timingData: Record<string, { startedAt: string; completedAt: string }>;
}

export interface AgentStats {
  totalThreads: number;
  running: number;
  completed: number;
  failed: number;
  interrupted: number;
  idle: number;
}

export interface GraphStats {
  graphId: string;
  totalRuns: number;
  succeeded: number;
  failed: number;
  running: number;
  successRate: number;
  lastRunAt: string | null;
}

export const OUTPUT_KEYS = [
  "research_output", "clinical_output", "gap_analysis_output",
  "learning_objectives_output", "needs_assessment_output", "curriculum_output",
  "protocol_output", "marketing_output", "grant_package_output",
  "prose_quality_pass_1", "prose_quality_pass_2", "compliance_result",
] as const;

export interface VsCandidate {
  content: string;
  probability: number;
}

export interface VsDistribution {
  distributionId: string;
  candidates: VsCandidate[];
  selectedIndex: number;
  confidence: number;
}

export async function listRunningAgents(): Promise<RunningAgent[]> {
  const client = createClient();
  const threads = await client.threads.search({
    status: "busy",
    limit: 50,
  });

  const results = await Promise.allSettled(
    threads.map(async (thread) => {
      const runs = await client.runs.list(thread.thread_id, { limit: 1 });
      const latestRun = runs[0];
      if (!latestRun) return null;
      let projectName = "";
      try {
        const state = await client.threads.getState(thread.thread_id);
        const vals = (state.values as Record<string, unknown>) ?? {};
        projectName = (vals.project_name as string) ?? "";
      } catch {
        // Thread state may not be available yet
      }
      return {
        threadId: thread.thread_id,
        runId: latestRun.run_id,
        graphId: (thread.metadata?.graph_id as string) ?? "unknown",
        status: latestRun.status as string,
        createdAt: thread.created_at,
        updatedAt: thread.updated_at,
        metadata: (thread.metadata as Record<string, unknown>) ?? {},
        projectName,
      } as RunningAgent;
    }),
  );

  const agents: RunningAgent[] = [];
  for (const r of results) {
    if (r.status === "fulfilled" && r.value) agents.push(r.value);
  }
  return agents;
}

export async function listAllAgents(): Promise<RunningAgent[]> {
  const client = createClient();
  const threads = await client.threads.search({ limit: 50 });

  const results = await Promise.allSettled(
    threads.map(async (thread) => {
      const runs = await client.runs.list(thread.thread_id, { limit: 1 });
      const latestRun = runs[0];
      let projectName = "";
      try {
        const state = await client.threads.getState(thread.thread_id);
        const vals = (state.values as Record<string, unknown>) ?? {};
        projectName = (vals.project_name as string) ?? "";
      } catch {
        // Thread state may not be available yet
      }
      return {
        threadId: thread.thread_id,
        runId: latestRun?.run_id ?? "",
        graphId: (thread.metadata?.graph_id as string) ?? "unknown",
        status: (latestRun?.status as string) ?? "idle",
        createdAt: thread.created_at,
        updatedAt: thread.updated_at,
        metadata: (thread.metadata as Record<string, unknown>) ?? {},
        projectName,
      } as RunningAgent;
    }),
  );

  const agents: RunningAgent[] = [];
  for (const r of results) {
    if (r.status === "fulfilled") agents.push(r.value);
  }
  return agents;
}

export async function listAssistants(): Promise<AssistantInfo[]> {
  const client = createClient();
  const assistants = await client.assistants.search({ limit: 50 });

  return assistants.map((a) => ({
    assistantId: a.assistant_id,
    graphId: a.graph_id,
    name: a.name ?? a.graph_id,
    createdAt: a.created_at,
  }));
}

/** Extract the Markdown document text from a structured agent output. */
function extractDocumentText(key: string, value: unknown): string {
  if (typeof value === "string") return value;
  if (!value || typeof value !== "object") return JSON.stringify(value);

  const obj = value as Record<string, unknown>;

  // Known document field mappings per output key
  const DOCUMENT_FIELDS: Record<string, string> = {
    research_output: "research_document",
    clinical_output: "clinical_practice_document",
    gap_analysis_output: "gap_analysis_document",
    learning_objectives_output: "learning_objectives_document",
    needs_assessment_output: "complete_document",
    curriculum_output: "curriculum_document",
    protocol_output: "protocol_document",
    marketing_output: "marketing_document",
    grant_package_output: "grant_package_document",
    prose_quality_pass_1: "document_text",
    prose_quality_pass_2: "document_text",
    compliance_result: "compliance_document",
  };

  // Try the known field first
  const knownField = DOCUMENT_FIELDS[key];
  if (knownField && typeof obj[knownField] === "string") {
    return obj[knownField] as string;
  }

  // Fallback: find any key ending in _document or _text with substantial content
  for (const [k, v] of Object.entries(obj)) {
    if (typeof v === "string" && v.length > 200 && (k.endsWith("_document") || k.endsWith("_text") || k === "complete_document")) {
      return v;
    }
  }

  // Fallback: last message content (agents store their narrative in messages)
  if (Array.isArray(obj.messages) && obj.messages.length > 0) {
    const last = obj.messages[obj.messages.length - 1] as Record<string, unknown>;
    if (typeof last?.content === "string" && last.content.length > 100) {
      return last.content as string;
    }
  }

  return JSON.stringify(value);
}

export async function getThreadState(threadId: string): Promise<ThreadState> {
  const client = createClient();
  const state = await client.threads.getState(threadId);
  const vals = (state.values as Record<string, unknown>) ?? {};

  const completedOutputs: string[] = [];
  const outputContents: Record<string, string> = {};
  for (const key of OUTPUT_KEYS) {
    if (vals[key] != null) {
      completedOutputs.push(key);
      outputContents[key] = extractDocumentText(key, vals[key]);
    }
  }

  const vsDistributions: Record<string, VsDistribution> = {};
  const rawVs = vals.vs_distributions as Record<string, unknown> | undefined;
  if (rawVs && typeof rawVs === "object") {
    for (const [stepName, dist] of Object.entries(rawVs)) {
      if (!dist || typeof dist !== "object") continue;
      const d = dist as Record<string, unknown>;
      const rawItems = (d.items as Array<Record<string, unknown>>) ?? [];
      const candidates: VsCandidate[] = rawItems.map((item) => ({
        content: (item.content as string) ?? "",
        probability: (item.probability as number) ?? 0,
      }));
      // All agents currently use strategy="argmax", so highest probability = selected
      const sorted = [...candidates].sort((a, b) => b.probability - a.probability);
      vsDistributions[stepName] = {
        distributionId: (d.distribution_id as string) ?? "",
        candidates,
        selectedIndex: candidates.length > 0
          ? candidates.indexOf(sorted[0])
          : -1,
        confidence: sorted.length > 0 ? sorted[0].probability : 0,
      };
    }
  }

  const timingData: Record<string, { startedAt: string; completedAt: string }> = {};
  const rawTiming = vals.agent_timing as Record<string, unknown> | undefined;
  if (rawTiming && typeof rawTiming === "object") {
    for (const [agentName, timing] of Object.entries(rawTiming)) {
      const t = timing as Record<string, unknown>;
      timingData[agentName] = {
        startedAt: (t.started_at as string) ?? "",
        completedAt: (t.completed_at as string) ?? "",
      };
    }
  }

  return {
    projectId: (vals.project_id as string) ?? "",
    projectName: (vals.project_name as string) ?? "",
    status: (vals.status as string) ?? "unknown",
    currentStep: (vals.current_step as string) ?? "",
    errors: (vals.errors as Array<Record<string, unknown>>) ?? [],
    completedOutputs,
    retryCount: (vals.retry_count as number) ?? 0,
    lastCheckpoint: (vals.last_checkpoint as string) ?? "",
    checkpointAgent: (vals.checkpoint_agent as string) ?? "",
    humanReviewStatus: (vals.human_review_status as string) ?? null,
    reviewRound: (vals.review_round as number) ?? 0,
    outputContents,
    vsDistributions,
    timingData,
  };
}

export async function getAgentStats(): Promise<AgentStats> {
  const client = createClient();
  const threads = await client.threads.search({ limit: 100 });

  const stats: AgentStats = {
    totalThreads: threads.length,
    running: 0,
    completed: 0,
    failed: 0,
    interrupted: 0,
    idle: 0,
  };

  for (const thread of threads) {
    const s = thread.status;
    if (s === "busy") stats.running++;
    else if (s === "idle") stats.idle++;
    else if (s === "interrupted") stats.interrupted++;
    else if (s === "error") stats.failed++;
    else stats.completed++;
  }

  return stats;
}

export async function getGraphStats(): Promise<GraphStats[]> {
  const client = createClient();
  const threads = await client.threads.search({ limit: 100 });

  const statsMap: Record<string, {
    totalRuns: number;
    succeeded: number;
    failed: number;
    running: number;
    lastRunAt: string | null;
  }> = {};

  for (const thread of threads) {
    const graphId = (thread.metadata?.graph_id as string) ?? "unknown";
    if (!statsMap[graphId]) {
      statsMap[graphId] = { totalRuns: 0, succeeded: 0, failed: 0, running: 0, lastRunAt: null };
    }
    const entry = statsMap[graphId];
    entry.totalRuns++;

    const s = thread.status;
    if (s === "busy") entry.running++;
    else if (s === "error") entry.failed++;
    else if (s === "idle" || s === "interrupted") entry.succeeded++;

    const updatedAt = thread.updated_at;
    if (updatedAt && (!entry.lastRunAt || updatedAt > entry.lastRunAt)) {
      entry.lastRunAt = updatedAt;
    }
  }

  return Object.entries(statsMap).map(([graphId, s]) => ({
    graphId,
    totalRuns: s.totalRuns,
    succeeded: s.succeeded,
    failed: s.failed,
    running: s.running,
    successRate: s.totalRuns > 0 ? Math.round((s.succeeded / s.totalRuns) * 100) : 0,
    lastRunAt: s.lastRunAt,
  }));
}

export async function retryAgent(threadId: string, graphId: string): Promise<string> {
  const client = createClient();
  const run = await client.runs.create(threadId, graphId, {});
  return run.run_id;
}

export async function getPreviousRunOutput(
  projectId: string,
  beforeDate: string,
  outputKey: string,
): Promise<string | null> {
  const client = createClient();
  const threads = await client.threads.search({ limit: 20 });

  for (const thread of threads) {
    if (new Date(thread.created_at) >= new Date(beforeDate)) continue;
    try {
      const state = await client.threads.getState(thread.thread_id);
      const vals = (state.values as Record<string, unknown>) ?? {};
      if ((vals.project_id as string) !== projectId) continue;
      const output = vals[outputKey];
      if (output == null) continue;
      return typeof output === "string" ? output : JSON.stringify(output);
    } catch {
      continue;
    }
  }

  return null;
}
