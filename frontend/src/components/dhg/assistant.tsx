"use client";

import { Thread } from "@/components/assistant-ui/thread";
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { useLangGraphRuntime } from "@assistant-ui/react-langgraph";
import { LangChainMessage } from "@assistant-ui/react-langgraph";

import { createThread, getThreadState, sendMessage } from "@/lib/chatApi";

interface AssistantProps {
  graphId: string;
}

export function Assistant({ graphId }: AssistantProps) {
  const runtime = useLangGraphRuntime({
    stream: async (messages, { initialize, ...config }) => {
      const { externalId } = await initialize();
      if (!externalId) throw new Error("Thread not found");
      return sendMessage({
        threadId: externalId,
        messages,
        graphId,
        config,
      });
    },
    create: async () => {
      const { thread_id } = await createThread();
      return { externalId: thread_id };
    },
    load: async (externalId) => {
      const state = await getThreadState(externalId);
      return {
        messages:
          (state.values as { messages?: LangChainMessage[] }).messages ?? [],
      };
    },
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <Thread />
    </AssistantRuntimeProvider>
  );
}
