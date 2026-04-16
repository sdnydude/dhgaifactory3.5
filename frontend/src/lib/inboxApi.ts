import { Client } from "@langchain/langgraph-sdk";
import type { ReviewPayload, ReviewPayloadWithVS, ResumeValue } from "@/components/review/types";

const createClient = () => {
  const envUrl = process.env.NEXT_PUBLIC_LANGGRAPH_API_URL ?? "/api/langgraph";
  const baseUrl = envUrl.startsWith("/")
    ? (typeof window !== "undefined" ? `${window.location.origin}${envUrl}` : `http://localhost:3000${envUrl}`)
    : envUrl;
  return new Client({ apiUrl: baseUrl });
};

export interface PendingReview {
  threadId: string;
  graphId: string;
  createdAt: string;
  payload: ReviewPayloadWithVS | null;
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
    let payload: ReviewPayloadWithVS | null = null;
    let currentStep = "unknown";
    let status = "awaiting_review";
    let hasInterrupt = false;

    try {
      const state = await client.threads.getState(thread.thread_id);
      const values = state.values as Record<string, unknown> | null;
      const tasks = state.tasks ?? [];
      const topInterrupts =
        (state as unknown as { interrupts?: unknown[] }).interrupts ?? [];

      for (const task of tasks) {
        if (task.interrupts && task.interrupts.length > 0) {
          hasInterrupt = true;
          for (const interrupt of task.interrupts) {
            const val = interrupt.value as ReviewPayloadWithVS;
            if (val && val.document) {
              payload = val;
            }
          }
        }
      }

      if (topInterrupts.length > 0) {
        hasInterrupt = true;
      }

      currentStep = (values?.current_step as string) ?? "unknown";
      status = (values?.status as string) ?? "awaiting_review";
    } catch {
      // getState can fail for individual threads (missing checkpoint,
      // schema mismatch). Skip silently — a thread we can't introspect
      // also can't be resumed by a human review decision.
      continue;
    }

    // Drop zombie threads: LangGraph marks a run as "interrupted" when
    // it halts for any reason (error, crash, pre-review stop). Only
    // threads with an actual interrupt payload are resumable by a
    // human decision, so only those belong in the review inbox.
    if (!hasInterrupt) {
      continue;
    }

    reviews.push({
      threadId: thread.thread_id,
      graphId: (thread.metadata?.graph_id as string) ?? "unknown",
      createdAt: thread.created_at,
      payload,
      currentStep,
      status,
    });
  }

  return reviews;
}

export async function resumeThread(
  threadId: string,
  graphId: string,
  resumeValue: ResumeValue,
) {
  const client = createClient();
  return client.runs.create(threadId, graphId, {
    input: null,
    command: { resume: resumeValue },
  });
}

export async function getThreadDetails(threadId: string) {
  const client = createClient();
  const state = await client.threads.getState(threadId);
  return state;
}
