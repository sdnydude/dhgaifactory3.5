# LangGraph Cloud Deployment Checklist

> **Created after build failures due to missing pyproject.toml**

## Before Creating/Updating a Deployment

### Required Files
- [ ] `pyproject.toml` exists with ALL dependencies
- [ ] `langgraph.json` exists and points to correct graph path
- [ ] `requirements.txt` matches pyproject.toml (for local dev)

### Dependencies Check
- [ ] All imports in agent code are in pyproject.toml dependencies
- [ ] No stdlib module name conflicts (e.g., don't name files `secrets.py`)
- [ ] No local-only packages (e.g., Ollama) unless cloud-compatible

### Secrets Handling
- [ ] Secrets are read from `os.environ`, NOT SDK calls
- [ ] No Infisical SDK imports (LangGraph Cloud injects env vars)
- [ ] All required secrets added to deployment config

### Graph Definition
- [ ] `graph` variable is exported from specified module
- [ ] StateGraph is properly compiled with `.compile()`
- [ ] No references to local files/paths

## Common Build Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `BUILD_FAILED` immediately | Missing pyproject.toml | Create with all deps |
| `ModuleNotFoundError` | Dep not in pyproject.toml | Add to dependencies |
| `ImportError: secrets` | File named `secrets.py` | Rename file |
| Connection errors | SDK trying to reach external | Use env vars |
