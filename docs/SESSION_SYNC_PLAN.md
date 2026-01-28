# Session Sync Integration Plan

**Date:** 2026-01-27  
**Goal:** Enable automatic syncing of Antigravity sessions to the database and LangSmith Cloud

---

## Current State

### What Exists
- **Registry API** running on port 8011 with Antigravity endpoints (`/api/v1/antigravity/chats`, `/files`)
- **Database tables** for `antigravity_chats` and `antigravity_files`
- **MCP Server** skeleton at `tools/mcp-servers/antigravity_mcp_server.py`
- **Sync script** at `tools/sync_antigravity_session.py` (manual, hardcoded)

### Issues Found
1. **Registry API bug:** Pydantic validation error - `tags` field expects list but gets None
2. **MCP Server:** Points to wrong port (8500 instead of 8011)
3. **Sync script:** Hardcoded session IDs and file paths

---

## Proposed Changes

### Phase 1: Fix Registry API Bug

#### [MODIFY] registry/schemas.py
- Make `tags` field Optional with default empty list

```python
tags: Optional[List[str]] = []
```

### Phase 2: Configure MCP Server

#### [MODIFY] tools/mcp-servers/antigravity_mcp_server.py
- Update `REGISTRY_URL` from `http://10.0.0.251:8500` to `http://10.0.0.251:8011`
- Add conversation_id tracking
- Add LangSmith trace integration

### Phase 3: LangSmith Integration

Add LangSmith tracing to session sync:
- Track session metadata as LangSmith run metadata
- Link conversation_id to LangSmith trace_id
- Send session summaries to LangSmith for cost tracking

#### [NEW] tools/langsmith_sync.py
```python
# Sync session data to both Registry and LangSmith
# - POST to Registry API for database storage
# - POST to LangSmith for trace metadata
# - Link conversation_id <-> trace_id
```

### Phase 4: Add to Observability

#### [MODIFY] observability/prometheus/prometheus.yml
Add scrape config for sync metrics:
```yaml
- job_name: antigravity-sync
  static_configs:
    - targets: [registry-api:8000]
  metrics_path: /metrics
```

#### [NEW] observability/grafana/dashboards/antigravity-sessions.json
Dashboard showing:
- Sessions synced per day
- Files tracked per session
- Sync errors/failures
- Database storage size

---

## Implementation Order

1. [ ] Fix registry/schemas.py Pydantic bug (5 min)
2. [ ] Rebuild registry-api container (2 min)
3. [ ] Verify /api/v1/antigravity/chats works
4. [ ] Update MCP server port config
5. [ ] Create langsmith_sync.py with proper integration
6. [ ] Add Prometheus metrics to registry-api
7. [ ] Create Grafana dashboard

---

## Verification

```bash
# Test registry endpoint after fix
curl http://10.0.0.251:8011/api/v1/antigravity/chats

# Create test session
curl -X POST http://10.0.0.251:8011/api/v1/antigravity/chats \
  -H "Content-Type: application/json" \
  -d {conversation_id: test-123, title: Test Session}
```

---

## Integration with LangSmith Cloud

Sessions will be linked via:
1. **conversation_id** in Registry database
2. **trace_id** in LangSmith 
3. **metadata.conversation_id** on LangSmith runs

This enables:
- Query LangSmith by conversation_id
- Query Registry by trace_id
- Full observability across both systems
