import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

const LANGGRAPH_CLOUD_URL =
  "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app";

const langGraphUrl =
  process.env.LANGGRAPH_API_URL || LANGGRAPH_CLOUD_URL;
const langSmithApiKey = process.env.LANGCHAIN_API_KEY;

const runtime = new CopilotRuntime({
  agents: {
    needs_assessment: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "needs_assessment",
      agentId: "needs_assessment",
      description:
        "Generates CME needs assessment documents with cold open framework and 3100+ word validation",
    }),
    research: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "research",
      agentId: "research",
      description:
        "Literature and PubMed research queries with 30+ sources",
    }),
    clinical_practice: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "clinical_practice",
      agentId: "clinical_practice",
      description:
        "Barrier identification and standard-of-care analysis",
    }),
    gap_analysis: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "gap_analysis",
      agentId: "gap_analysis",
      description:
        "Identifies 5+ evidence-based practice gaps with quantification and severity scoring",
    }),
    learning_objectives: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "learning_objectives",
      agentId: "learning_objectives",
      description:
        "Moore's Expanded Framework mapping for learning objectives",
    }),
    curriculum_design: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "curriculum_design",
      agentId: "curriculum_design",
      description:
        "Educational design with innovation section",
    }),
    research_protocol: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "research_protocol",
      agentId: "research_protocol",
      description:
        "IRB-ready outcomes research protocol",
    }),
    marketing_plan: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "marketing_plan",
      agentId: "marketing_plan",
      description:
        "Audience strategy and channel budget planning",
    }),
    grant_writer: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "grant_writer",
      agentId: "grant_writer",
      description:
        "Full grant package assembly",
    }),
    prose_quality: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "prose_quality",
      agentId: "prose_quality",
      description:
        "De-AI-ification scoring and banned pattern detection for prose quality",
    }),
    compliance_review: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "compliance_review",
      agentId: "compliance_review",
      description:
        "ACCME compliance verification",
    }),
    needs_package: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "needs_package",
      agentId: "needs_package",
      description:
        "Research + Clinical parallel, then Gap, LO, Needs, and Prose QA",
    }),
    curriculum_package: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
      graphId: "curriculum_package",
      agentId: "curriculum_package",
      description:
        "Needs Package + Curriculum + Protocol + Marketing parallel",
    }),
    grant_package: new LangGraphAgent({
      deploymentUrl: langGraphUrl,
      langsmithApiKey: langSmithApiKey,
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
