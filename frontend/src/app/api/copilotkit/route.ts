import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

const langGraphUrl =
  process.env.LANGGRAPH_API_URL || "http://localhost:2026";

const runtime = new CopilotRuntime({
  agents: {
    needs_assessment: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      graphId: "needs_assessment",
      agentId: "needs_assessment",
      description:
        "Generates CME needs assessment documents with cold open framework and 3100+ word validation",
    }),
    gap_analysis: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      graphId: "gap_analysis",
      agentId: "gap_analysis",
      description:
        "Identifies evidence-based practice gaps with quantification and severity scoring",
    }),
    needs_package: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      graphId: "needs_package",
      agentId: "needs_package",
      description:
        "Orchestrates Research + Clinical parallel, then Gap, LO, Needs, and Prose QA",
    }),
    grant_package: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      graphId: "grant_package",
      agentId: "grant_package",
      description:
        "Full 11-agent pipeline with Prose QA passes, Compliance gate, and Human Review",
    }),
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
