# SOP: LangGraph Cloud & LangSmith Suite

**Version:** 3.0.0 (Apr 8, 2026)
**Platform:** LangGraph Cloud + LangSmith Studio

## 1. Overview
DHG AI Factory utilizes LangGraph Cloud for agent orchestration and LangSmith for observability, debugging, and quality evaluation.

## 2. Configuration (`langgraph.json`)
Every cloud-ready agent must have a `langgraph.json` in its root:
- `path`: Points to the compiled graph (`src/agent.py:graph`).
- `env`: Specifies the `.env` file location.
- `dependencies`: Lists all required Python packages.

## 3. Pre-Deployment Checklist

Run through this before every deployment. Created after build failures caused by missing files and dependency issues.

### Required Files
- [ ] `pyproject.toml` exists with ALL dependencies
- [ ] `langgraph.json` exists and points to correct graph path
- [ ] `requirements.txt` matches pyproject.toml (for local dev)

### Dependencies
- [ ] All imports in agent code are listed in pyproject.toml dependencies
- [ ] No stdlib module name conflicts (e.g., don't name a file `secrets.py` — shadows the stdlib `secrets` module)
- [ ] No local-only packages (e.g., Ollama Python client) unless they are cloud-compatible

### Secrets
- [ ] Secrets are read from `os.environ` or `os.getenv()`, NOT SDK calls
- [ ] No Infisical SDK imports — LangGraph Cloud injects env vars directly
- [ ] All required secrets added to the LangGraph Cloud deployment config

### Graph Definition
- [ ] `graph` variable is exported from the module specified in `langgraph.json`
- [ ] StateGraph is properly compiled with `.compile()`
- [ ] No references to local file paths or host-specific resources

## 4. LangSmith Studio Integration
1. **Tracing**: Ensure `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set.
2. **Projects**: Traces should be routed to a specific project (e.g., `dhg-cme-research`).
3. **Playground**: Test the graph in LangSmith Studio for rapid iteration.
4. **Assistants**: Configure assistants in the Studio UI to map to specific graph versions.

## 5. Debugging with Trace IDs
When an error occurs:
1. Capture the **Trace ID** from the logs or Studio UI.
2. Search for the Trace ID in LangSmith to pinpoint the failing node.
3. Review inputs/outputs for that specific node.

## 6. Deployment Workflow
1. **Pre-flight**: Run through Section 3 checklist.
2. **Local Dev**: Run `langgraph dev --host 0.0.0.0 --port 2026` or `docker compose up -d` in `langgraph_workflows/dhg-agents-cloud/`.
3. **Verification**: `curl http://localhost:2026/ok` and test via LangSmith Studio.
4. **Commit**: Push to `master` branch.
5. **Deploy**: Auto-deployment to LangGraph Cloud via GitHub integration.
6. **Production URL**: `https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` (auth via `x-api-key` header with `LANGCHAIN_API_KEY`).

## 7. Common Build Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `BUILD_FAILED` immediately | Missing pyproject.toml | Create with all deps |
| `ModuleNotFoundError` | Dependency not in pyproject.toml | Add to dependencies |
| `ImportError: secrets` | File named `secrets.py` shadows stdlib | Rename the file |
| Connection errors at startup | SDK trying to reach external service | Use env vars, not SDK calls |

## 8. Best Practices
- Use `@traceable` on all critical functions.
- Mask secrets in logs.
- Utilize "Datasets" in LangSmith for regression testing.
