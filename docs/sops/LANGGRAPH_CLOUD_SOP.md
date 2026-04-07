# SOP: LangGraph Cloud & LangSmith Suite

**Version:** 2.0.0 (Apr 6, 2026)
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
1. **Local Dev**: Run `langgraph dev --host 0.0.0.0 --port 2026` or `docker compose up -d` in `langgraph_workflows/dhg-agents-cloud/`.
2. **Verification**: `curl http://localhost:2026/ok` and test via LangSmith Studio.
3. **Commit**: Push to `master` branch.
4. **Deploy**: Auto-deployment to LangGraph Cloud via GitHub integration.
5. **Production URL**: `https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` (auth via `x-api-key` header with `LANGCHAIN_API_KEY`).

## 6. Best Practices
- Use `@traceable` on all critical functions.
- Mask secrets in logs.
- Utilize "Datasets" in LangSmith for regression testing.
