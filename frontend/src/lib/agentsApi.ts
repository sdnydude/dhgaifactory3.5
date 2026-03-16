import { Client } from "@langchain/langgraph-sdk";

const createClient = () => {
  const baseUrl = process.env.NEXT_PUBLIC_LANGGRAPH_API_URL ||
    (typeof window !== "undefined" ? `${window.location.origin}/api/langgraph` : "http://localhost:3000/api/langgraph");
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

export const OUTPUT_KEYS = [
  "research_output", "clinical_output", "gap_analysis_output",
  "learning_objectives_output", "needs_assessment_output", "curriculum_output",
  "protocol_output", "marketing_output", "grant_package_output",
  "prose_quality_pass_1", "prose_quality_pass_2", "compliance_result",
] as const;

export interface VsCandidate {
  name: string;
  description: string;
  score: number;
}

export interface VsDistribution {
  agentName: string;
  selected: VsCandidate;
  candidates: VsCandidate[];
}

export async function listRunningAgents(): Promise<RunningAgent[]> {
  const client = createClient();
  const threads = await client.threads.search({
    status: "busy",
    limit: 50,
  });

  const agents: RunningAgent[] = [];

  for (const thread of threads) {
    const runs = await client.runs.list(thread.thread_id, { limit: 1 });
    const latestRun = runs[0];
    if (latestRun) {
      let projectName = "";
      try {
        const state = await client.threads.getState(thread.thread_id);
        const vals = (state.values as Record<string, unknown>) ?? {};
        projectName = (vals.project_name as string) ?? "";
      } catch {
        // Thread state may not be available yet
      }
      agents.push({
        threadId: thread.thread_id,
        runId: latestRun.run_id,
        graphId: (thread.metadata?.graph_id as string) ?? "unknown",
        status: latestRun.status,
        createdAt: thread.created_at,
        updatedAt: thread.updated_at,
        metadata: (thread.metadata as Record<string, unknown>) ?? {},
        projectName,
      });
    }
  }

  return agents;
}

export async function listAllAgents(): Promise<RunningAgent[]> {
  const client = createClient();
  const threads = await client.threads.search({ limit: 50 });

  const agents: RunningAgent[] = [];

  for (const thread of threads) {
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
    agents.push({
      threadId: thread.thread_id,
      runId: latestRun?.run_id ?? "",
      graphId: (thread.metadata?.graph_id as string) ?? "unknown",
      status: latestRun?.status ?? "idle",
      createdAt: thread.created_at,
      updatedAt: thread.updated_at,
      metadata: (thread.metadata as Record<string, unknown>) ?? {},
      projectName,
    });
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

export async function getThreadState(threadId: string): Promise<ThreadState> {
  const client = createClient();
  const state = await client.threads.getState(threadId);
  const vals = (state.values as Record<string, unknown>) ?? {};

  const completedOutputs: string[] = [];
  const outputContents: Record<string, string> = {};
  for (const key of OUTPUT_KEYS) {
    if (vals[key] != null) {
      completedOutputs.push(key);
      outputContents[key] = typeof vals[key] === "string"
        ? (vals[key] as string)
        : JSON.stringify(vals[key]);
    }
  }

  const vsDistributions: Record<string, VsDistribution> = {};
  const rawVs = vals.vs_distributions as Record<string, unknown> | undefined;
  if (rawVs && typeof rawVs === "object") {
    for (const [agentName, dist] of Object.entries(rawVs)) {
      const d = dist as Record<string, unknown>;
      vsDistributions[agentName] = {
        agentName: (d.agent_name as string) ?? agentName,
        selected: (d.selected as VsCandidate) ?? { name: "", description: "", score: 0 },
        candidates: (d.candidates as VsCandidate[]) ?? [],
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

export async function retryAgent(threadId: string): Promise<string> {
  const client = createClient();
  const run = await client.runs.create(threadId, "needs_package", {});
  return run.run_id;
}

export async function getPreviousRunOutput(
  projectId: string,
  beforeDate: string,
  outputKey: string,
): Promise<string | null> {
  const client = createClient();
  const threads = await client.threads.search({ limit: 100 });

  for (const thread of threads) {
    if (thread.created_at >= beforeDate) continue;
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
