import { Client } from "@langchain/langgraph-sdk";
import {
  LangChainMessage,
  LangGraphSendMessageConfig,
} from "@assistant-ui/react-langgraph";

const createClient = () => {
  return new Client({
    apiUrl: process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "/api/langgraph",
  });
};

export const createThread = async () => {
  const client = createClient();
  return client.threads.create();
};

export const getThreadState = async (threadId: string) => {
  const client = createClient();
  return client.threads.getState(threadId);
};

export const sendMessage = async (params: {
  threadId: string;
  messages: LangChainMessage[];
  graphId: string;
  config?: LangGraphSendMessageConfig;
}) => {
  const client = createClient();
  const { checkpointId, ...restConfig } = params.config ?? {};
  return client.runs.stream(params.threadId, params.graphId, {
    input: params.messages.length > 0 ? { messages: params.messages } : null,
    streamMode: "messages-tuple",
    ...(checkpointId && { checkpoint_id: checkpointId }),
    ...restConfig,
  });
};

export const listGraphs = async (): Promise<string[]> => {
  const client = createClient();
  const assistants = await client.assistants.search();
  return assistants.map((a) => a.graph_id);
};
