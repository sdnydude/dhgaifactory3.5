import { Client } from "@langchain/langgraph-sdk";

const createClient = () => {
  return new Client({
    apiUrl: process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "/api/langgraph",
  });
};

export interface RunningAgent {
  threadId: string;
  runId: string;
  graphId: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  metadata: Record<string, unknown>;
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
}

export interface AgentStats {
  totalThreads: number;
  running: number;
  completed: number;
  failed: number;
  interrupted: number;
  idle: number;
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
      agents.push({
        threadId: thread.thread_id,
        runId: latestRun.run_id,
        graphId: (thread.metadata?.graph_id as string) ?? "unknown",
        status: latestRun.status,
        createdAt: thread.created_at,
        updatedAt: thread.updated_at,
        metadata: (thread.metadata as Record<string, unknown>) ?? {},
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
    agents.push({
      threadId: thread.thread_id,
      runId: latestRun?.run_id ?? "",
      graphId: (thread.metadata?.graph_id as string) ?? "unknown",
      status: latestRun?.status ?? "idle",
      createdAt: thread.created_at,
      updatedAt: thread.updated_at,
      metadata: (thread.metadata as Record<string, unknown>) ?? {},
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

  const outputKeys = Object.keys(vals).filter(
    (k) => k.endsWith("_output") && vals[k] != null,
  );

  return {
    projectId: (vals.project_id as string) ?? "",
    projectName: (vals.project_name as string) ?? "",
    status: (vals.status as string) ?? "unknown",
    currentStep: (vals.current_step as string) ?? "",
    errors: (vals.errors as Array<Record<string, unknown>>) ?? [],
    completedOutputs: outputKeys,
    retryCount: (vals.retry_count as number) ?? 0,
    lastCheckpoint: (vals.last_checkpoint as string) ?? "",
    checkpointAgent: (vals.checkpoint_agent as string) ?? "",
    humanReviewStatus: (vals.human_review_status as string) ?? null,
    reviewRound: (vals.review_round as number) ?? 0,
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
