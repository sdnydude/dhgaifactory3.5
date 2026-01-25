# SOP: LangGraph Cloud & LangSmith Suite

**Version:** 1.0.0 (Jan 25, 2026)
**Platform:** LangGraph Cloud + LangSmith Studio

## 1. Overview
DHG AI Factory utilizes LangGraph Cloud for agent orchestration and LangSmith for observability, debugging, and quality evaluation.

## 2. Configuration (`langgraph.json`)
Every cloud-ready agent must have a `langgraph.json` in its root:
- `path`: Points to the compiled graph (`src/agent.py:graph`).
- `env`: Specifies the `.env` file location.
- `dependencies`: Lists all required Python packages.

## 3. LangSmith Studio Integration
1. **Tracing**: Ensure `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set.
2. **Projects**: Traces should be routed to a specific project (e.g., `dhg-cme-research`).
3. **Playground**: Test the graph in LangSmith Studio for rapid iteration.
4. **Assistants**: Configure assistants in the Studio UI to map to specific graph versions.

## 4. Debugging with Trace IDs
When an error occurs:
1. Capture the **Trace ID** from the logs or Studio UI.
2. Search for the Trace ID in LangSmith to pinpoint the failing node.
3. Review inputs/outputs for that specific node.

## 5. Deployment Workflow
1. **Local Dev**: Run `langgraph dev --host 0.0.0.0 --port 2026`.
2. **Verification**: Confirm registry registration.
3. **Commit**: Push to `feature/langgraph-migration`.
4. **Deploy**: Auto-deployment to LangGraph Cloud via GitHub integration.

## 6. Best Practices
- Use `@traceable` on all critical functions.
- Mask secrets in logs.
- Utilize "Datasets" in LangSmith for regression testing.
