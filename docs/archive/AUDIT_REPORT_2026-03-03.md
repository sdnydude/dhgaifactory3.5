# DHG AI Factory Production Code Audit Report
**Date:** March 3, 2026
**Auditor:** Claude Opus 4.5
**Server:** g700data1 (Ubuntu 24.04, RTX 5080, 64GB RAM)

---

## Executive Summary

This audit reveals **3 CRITICAL**, **9 MAJOR**, and **6 MINOR** issues across the DHG AI Factory codebase. The most severe problems involve network connectivity failures between services, zero authentication on API endpoints, and significant architectural confusion between Gen 1 (WebSocket agents) and Gen 2 (LangGraph) systems.

---

## CRITICAL Issues (3)

### C1. Port 8011 Conflict - Services Cannot Start Together
**Location:** `docker-compose.override.yml:59-60` vs orchestrator design
**Impact:** Gen 2 orchestrator cannot run because registry-api claims port 8011

```yaml
# docker-compose.override.yml:59-60
registry-api:
  ...
  ports:
    - "8011:8000"  # <-- BLOCKING orchestrator's port
```

**Fix:**
```yaml
# Change registry-api to different port
ports:
  - "8500:8000"  # Use intended registry port
```

---

### C2. LangGraph Container Network Isolation
**Location:** `langgraph_workflows/dhg-agents-cloud/docker-compose.yml:19-22`
**Impact:** LangGraph agents cannot reach PostgreSQL, registry, or any other services

```yaml
# langgraph_workflows/dhg-agents-cloud/docker-compose.yml:19-22
environment:
  AI_FACTORY_REGISTRY_URL: http://host.docker.internal:8500  # Nothing listens on 8500
  DATABASE_URL: postgresql://dhg:${POSTGRES_PASSWORD}@host.docker.internal:5432/dhg_registry
```

**Problem:** Container is on its own Docker network, `host.docker.internal` only works on macOS/Windows, not Linux.

**Fix:**
```yaml
# Add to langgraph docker-compose.yml
networks:
  default:
    external:
      name: dhgaifactory35_default  # Join main docker network
```

And change to Docker DNS names:
```yaml
environment:
  AI_FACTORY_REGISTRY_URL: http://dhg-registry-api:8000
  DATABASE_URL: postgresql://dhg:${POSTGRES_PASSWORD}@dhg-registry-db:5432/dhg_registry
```

---

### C3. Registry API Has ZERO Authentication
**Location:** `registry/api.py:266-272`
**Impact:** Anyone can read/write CME projects, reviewer data, and trigger workflows

```python
# registry/api.py:266-272
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # WIDE OPEN
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**All 47 endpoints** including sensitive ones like:
- `POST /reviewers` - Create reviewers
- `POST /projects/{id}/submit-for-review` - Trigger workflows
- `POST /langgraph/webhook` - External webhook (no auth!)

**Fix:** Add authentication middleware:
```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not verify_jwt(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials
```

---

## MAJOR Issues (9)

### M1. Inconsistent Default Passwords Across Codebase
**Locations:**
- `docker-compose.override.yml:52` -> `POSTGRES_PASSWORD=weenie64`
- `registry/database.py:12` -> `DB_PASS = os.getenv("POSTGRES_PASSWORD", "changeme")`
- `registry/api.py:85` -> `password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "weenie64")`

**Impact:** Connection failures or security exposure depending on which file's default is used.

**Fix:** Remove all hardcoded defaults, require environment variable:
```python
# registry/database.py:12
DB_PASS = os.getenv("POSTGRES_PASSWORD")
if not DB_PASS:
    raise ValueError("POSTGRES_PASSWORD environment variable required")
```

---

### M2. Web-UI Hardcoded Server IP
**Location:** `web-ui/src/App.jsx:71` and `web-ui/src/context/StudioContext.jsx:52`

```javascript
// App.jsx:71
const response = await fetch('http://10.0.0.251:8011/api/ollama/chat', {

// StudioContext.jsx:52
const response = await fetch('http://10.0.0.251:8011/api/ollama/models');
```

**Impact:** App only works when running on server 10.0.0.251

**Fix:** Use environment variable:
```javascript
const API_URL = import.meta.env.VITE_API_URL || window.location.origin;
const response = await fetch(`${API_URL}/api/ollama/chat`, {
```

---

### M3. LangGraph URL Misconfiguration
**Location:** `registry/cme_endpoints.py:264`

```python
# registry/cme_endpoints.py:264
langgraph_url = os.getenv("LANGGRAPH_API_URL", "http://localhost:8011/langgraph/run")
```

**Impact:** When running in Docker, `localhost` refers to the container itself, not the LangGraph service.

**Fix:**
```python
langgraph_url = os.getenv("LANGGRAPH_API_URL", "http://dhg-langgraph:8123/langgraph/run")
```

---

### M4. WebSocket URL in useWebSocket.js Connects to Wrong Endpoint
**Location:** `web-ui/src/hooks/useWebSocket.js` + `web-ui/src/App.jsx:45`

```javascript
// App.jsx:45
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
return `${protocol}//${window.location.host}/ws`;
```

**Impact:** Falls back to current host's `/ws` which may not have a WebSocket endpoint.

**Fix:** Require explicit configuration:
```javascript
const WS_URL = import.meta.env.VITE_WS_URL;
if (!WS_URL) {
  console.error('VITE_WS_URL environment variable required');
}
```

---

### M5. Gen 1 vs Gen 2 Architecture Confusion
**Impact:** 15 Gen 1 agents (WebSocket) exist alongside 19 LangGraph agents, creating confusion about which to use.

**Gen 1 Agents (ports 8002-8012):**
- `/agents/medical-llm/`, `/agents/research/`, `/agents/curriculum/`, etc.
- WebSocket-based
- Running but not integrated with LangGraph

**Gen 2 Agents (LangGraph):**
- `/langgraph_workflows/dhg-agents-cloud/src/` (19 .py files)
- StateGraph-based
- Should replace Gen 1

**Fix:** Either:
1. Mark Gen 1 agents as deprecated in CLAUDE.md
2. Or remove Gen 1 from docker-compose.yml and migrate fully to LangGraph

---

### M6. TODO Markers in Production Code
**Locations:**
- `main.py:476` -> `# TODO: Implement registry logging`
- `agents/orchestrator/main.py:524` -> `# TODO: Implement registry logging`
- `agents/orchestrator/websocket_manager.py:132` -> `# TODO: Integrate with orchestrator`
- `registry/websocket_manager.py:132` -> `# TODO: Integrate with orchestrator`
- `agents/qa-compliance/main.py:385,391` -> `# TODO: Log to registry`, `recommendations=None`

**Impact:** Missing functionality that may be expected to work.

---

### M7. Archive Directory Contains Dead Code
**Location:** `/langgraph_workflows/Archive/`

Contents:
- `dhg-cme-research-agent/` (7 .py files)
- `dhg-cme-research-agent-cloud/` (2 .py files)
- 2 ZIP files with Mac resource forks (`._*` files)
- `.DS_Store` file

**Fix:** Either delete Archive or move to separate branch:
```bash
rm -rf langgraph_workflows/Archive/
```

---

### M8. Backup Files Committed to Repository
**Files found:**
- `agents/visuals/main.py.bak`
- `agents/qa-compliance/main.py.backup`
- `dhg-ai-factory-ui/src/App.tsx.backup`
- `docker-compose.yml.bak`
- `observability/prometheus/prometheus.yml.bak`
- `WARP.md.backup`
- `langgraph_workflows/dhg-agents-cloud/src/agent.py.backup`

**Fix:** Add to `.gitignore` and remove:
```bash
echo "*.bak" >> .gitignore
echo "*.backup" >> .gitignore
git rm --cached $(find . -name "*.bak" -o -name "*.backup")
```

---

### M9. Minimal Test Coverage
**Findings:**
- Only 2 test files in entire project:
  - `registry/test_review_workflow.py` (499 lines, mock-based unit tests)
  - `test_ws_client.py` (25 lines, manual WebSocket test)
- No tests for:
  - LangGraph agents (19 files, 0 tests)
  - Registry API endpoints (47 endpoints, 0 tests)
  - Web-UI components

**Impact:** Changes can break production without warning.

---

## MINOR Issues (6)

### N1. .DS_Store Files in Repository
**Locations:**
- `agents/.DS_Store`
- `langgraph_workflows/Archive/.DS_Store`
- Multiple `._*` macOS resource fork files

**Fix:**
```bash
find . -name ".DS_Store" -delete
find . -name "._*" -delete
echo ".DS_Store" >> .gitignore
echo "._*" >> .gitignore
```

---

### N2. Duplicate Agent Implementations
- `research_agent.py` exists in both Gen 1 (`agents/research/`) and Gen 2 (`langgraph_workflows/dhg-agents-cloud/src/`)
- `needs_assessment` exists in both systems
- Creates confusion about authoritative version

---

### N3. Inconsistent Environment Variable Names
- `POSTGRES_PASSWORD` vs `DB_PASSWORD` used interchangeably
- `LANGGRAPH_API_URL` vs `AI_FACTORY_REGISTRY_URL`
- No central documentation of required env vars

---

### N4. WebSocket test_ws_client.py Uses Hardcoded IP
**Location:** `test_ws_client.py:6`
```python
uri = "ws://10.0.0.251:8011/ws"
```

---

### N5. Missing Error Handling in LangGraph Agents
**Location:** `compliance_review_agent.py:242-248`
```python
try:
    data = json.loads(result["content"])
except:
    # Fallback default - bare except catches everything
    data = {...}
```

**Fix:** Catch specific exception:
```python
except json.JSONDecodeError as e:
    logger.warning(f"Failed to parse compliance response: {e}")
    data = {...}
```

---

### N6. Venv Directories Not Properly Gitignored
**Locations:**
- `langgraph_workflows/dhg-agents-cloud/venv/` (in git status)
- `langgraph_workflows/research/venv/`
- `scripts/.venv/`

---

## Summary Table

| Severity | Count | Key Areas |
|----------|-------|-----------|
| CRITICAL | 3 | Port conflict, Network isolation, No auth |
| MAJOR | 9 | Passwords, URLs, Architecture, Testing |
| MINOR | 6 | Hygiene, Duplicates, Error handling |

---

## Recommended Fix Priority

### Immediate (Day 1)
- Fix port 8011 conflict (C1)
- Add authentication to registry-api (C3)
- Fix LangGraph network isolation (C2)

### This Week
- Remove hardcoded IPs from Web-UI (M2)
- Consolidate password handling (M1)
- Fix LangGraph URL configuration (M3)

### This Sprint
- Clean up backup files and Archive (M7, M8)
- Add basic test coverage for critical paths (M9)
- Document Gen 1 vs Gen 2 migration path (M5)

### Ongoing
- Address TODO markers (M6)
- Fix minor hygiene issues (N1-N6)

---

## Files Examined

### Docker & Infrastructure
- `docker-compose.yml`
- `docker-compose.override.yml`
- `langgraph_workflows/dhg-agents-cloud/docker-compose.yml`

### LangGraph Agents
- `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py`
- `langgraph_workflows/dhg-agents-cloud/src/research_agent.py`
- `langgraph_workflows/dhg-agents-cloud/src/needs_assessment_agent.py`
- `langgraph_workflows/dhg-agents-cloud/src/compliance_review_agent.py`

### Registry API
- `registry/api.py`
- `registry/database.py`
- `registry/cme_endpoints.py`

### Web-UI
- `web-ui/src/App.jsx`
- `web-ui/src/hooks/useWebSocket.js`
- `web-ui/src/context/StudioContext.jsx`
- `web-ui/src/components/ChatArea.jsx`

### Tests
- `registry/test_review_workflow.py`
- `test_ws_client.py`
