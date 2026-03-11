/**
 * CopilotKit runtime configuration for DHG AI Factory.
 *
 * The CopilotKit runtime connects to LangGraph agents via the AG-UI protocol,
 * enabling generative UI — agents can render structured panels instead of plain text.
 *
 * Runtime URL: /api/copilotkit (Next.js API route)
 * LangGraph URL: LANGGRAPH_API_URL env var (default: http://localhost:2026)
 */

export const COPILOT_RUNTIME_URL = "/api/copilotkit";

/** Available agents for CopilotKit generative UI */
export const COPILOT_AGENTS = [
  "needs_assessment",
  "gap_analysis",
  "needs_package",
  "grant_package",
] as const;

export type CopilotAgentId = (typeof COPILOT_AGENTS)[number];
