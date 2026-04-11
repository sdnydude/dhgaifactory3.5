import { Client } from "@langchain/langgraph-sdk";

const createClient = () => {
  const envUrl = process.env.NEXT_PUBLIC_LANGGRAPH_API_URL ?? "/api/langgraph";
  const baseUrl = envUrl.startsWith("/")
    ? (typeof window !== "undefined" ? `${window.location.origin}${envUrl}` : `http://localhost:3000${envUrl}`)
    : envUrl;
  return new Client({ apiUrl: baseUrl });
};

export interface StreamEvent {
  id: string;
  timestamp: string;
  eventType: string;
  agentName: string;
  message: string;
  level: "info" | "warn" | "error" | "debug";
  tokenUsage?: { inputTokens: number; outputTokens: number };
}

let eventCounter = 0;

function formatTime(): string {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function parseStreamEvent(event: Record<string, unknown>): StreamEvent | null {
  const eventType = event.event as string;
  const name = (event.name as string) ?? "unknown";
  const id = `evt-${++eventCounter}`;
  const timestamp = formatTime();

  switch (eventType) {
    case "on_chain_start":
      return { id, timestamp, eventType, agentName: name, message: "Starting...", level: "info" };
    case "on_chain_end":
      return { id, timestamp, eventType, agentName: name, message: "\u2713 Complete", level: "info" };
    case "on_tool_start":
      return { id, timestamp, eventType, agentName: name, message: `Calling ${name}...`, level: "debug" };
    case "on_tool_end":
      return { id, timestamp, eventType, agentName: name, message: "Tool result received", level: "debug" };
    case "on_llm_end": {
      const output = event.data as Record<string, unknown> | undefined;
      const usage = output?.usage_metadata as { input_tokens?: number; output_tokens?: number } | undefined;
      if (usage) {
        return {
          id, timestamp, eventType, agentName: name,
          message: `LLM complete (${usage.input_tokens ?? 0} in / ${usage.output_tokens ?? 0} out)`,
          level: "debug",
          tokenUsage: {
            inputTokens: usage.input_tokens ?? 0,
            outputTokens: usage.output_tokens ?? 0,
          },
        };
      }
      return null;
    }
    case "on_llm_stream": {
      const chunk = event.data as Record<string, unknown> | undefined;
      const content = (chunk?.content as string) ?? "";
      if (!content) return null;
      return { id, timestamp, eventType, agentName: name, message: content, level: "info" };
    }
    default:
      return null;
  }
}

export async function resolveRunId(threadId: string): Promise<string | null> {
  const client = createClient();
  const runs = await client.runs.list(threadId, { limit: 1 });
  return runs[0]?.run_id ?? null;
}

export async function connectStream(
  threadId: string,
  onEvent: (event: StreamEvent) => void,
  onEnd: () => void,
  signal: AbortSignal,
): Promise<void> {
  const runId = await resolveRunId(threadId);
  if (!runId) {
    onEnd();
    return;
  }

  const client = createClient();
  let batchBuffer: StreamEvent[] = [];
  let batchTimer: ReturnType<typeof setTimeout> | null = null;

  const flushBatch = () => {
    for (const evt of batchBuffer) {
      onEvent(evt);
    }
    batchBuffer = [];
    batchTimer = null;
  };

  try {
    // joinStream connects to an already-running run's event stream
    const stream = client.runs.joinStream(threadId, runId, {
      signal,
      streamMode: "events",
    });

    for await (const chunk of stream) {
      if (signal.aborted) break;

      const event = chunk as unknown as Record<string, unknown>;
      const parsed = parseStreamEvent(event);
      if (!parsed) continue;

      if (parsed.eventType === "on_llm_stream") {
        batchBuffer.push(parsed);
        if (!batchTimer) {
          batchTimer = setTimeout(flushBatch, 200);
        }
      } else {
        if (batchTimer) {
          clearTimeout(batchTimer);
          flushBatch();
        }
        onEvent(parsed);
      }
    }

    if (batchTimer) {
      clearTimeout(batchTimer);
      flushBatch();
    }
  } catch (e) {
    if (!signal.aborted) {
      onEvent({
        id: `evt-${++eventCounter}`,
        timestamp: formatTime(),
        eventType: "error",
        agentName: "system",
        message: `Stream error: ${(e as Error).message}`,
        level: "error",
      });
    }
  } finally {
    onEnd();
  }
}
