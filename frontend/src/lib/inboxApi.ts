import { Client } from "@langchain/langgraph-sdk";
import type { ReviewPayload, ResumeValue } from "@/components/review/types";

const createClient = () => {
  return new Client({
    apiUrl:
      process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "http://localhost:2026",
  });
};

export interface PendingReview {
  threadId: string;
  graphId: string;
  createdAt: string;
  payload: ReviewPayload | null;
  currentStep: string;
  status: string;
}

export async function listPendingReviews(): Promise<PendingReview[]> {
  const client = createClient();
  const threads = await client.threads.search({
    status: "interrupted",
    limit: 50,
  });

  const reviews: PendingReview[] = [];

  for (const thread of threads) {
    const state = await client.threads.getState(thread.thread_id);
    const values = state.values as Record<string, unknown> | null;
    const tasks = state.tasks ?? [];

    let payload: ReviewPayload | null = null;
    for (const task of tasks) {
      if (task.interrupts) {
        for (const interrupt of task.interrupts) {
          const val = interrupt.value as ReviewPayload;
          if (val && val.document) {
            payload = val;
          }
        }
      }
    }

    if (payload || tasks.some((t) => t.interrupts?.length)) {
      reviews.push({
        threadId: thread.thread_id,
        graphId: (thread.metadata?.graph_id as string) ?? "unknown",
        createdAt: thread.created_at,
        payload,
        currentStep: (values?.current_step as string) ?? "unknown",
        status: (values?.status as string) ?? "awaiting_review",
      });
    }
  }

  return reviews;
}

export async function resumeThread(
  threadId: string,
  graphId: string,
  resumeValue: ResumeValue,
) {
  const client = createClient();
  return client.runs.stream(threadId, graphId, {
    input: null,
    command: { resume: resumeValue },
    streamMode: "messages-tuple",
  });
}

export async function getThreadDetails(threadId: string) {
  const client = createClient();
  const state = await client.threads.getState(threadId);
  return state;
}
