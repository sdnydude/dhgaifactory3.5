# DHG Repo Restructuring Plan

**Goal:** Scalable, portable agent architecture

---

## Current Structure (Monorepo)
```
dhgaifactory3.5/
├── agents/              # Docker agents mixed together
├── langgraph_workflows/ # Cloud agents separate
├── registry/            # Central registry
└── tools/
```

**Problems:** No independent versioning, mixed deploy targets, hard to scale.

---

## Target Structure (Multi-Repo)

```
github.com/sdnydude/
│
├── dhg-core/                    # Shared library (pip installable)
│   ├── dhg_core/
│   │   ├── schemas/             # Pydantic models
│   │   ├── registry_client/     # Registry API client
│   │   └── llm_utils/           # Common helpers
│   └── pyproject.toml
│
├── dhg-registry/                # Central Registry (standalone)
│   ├── api/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── dhg-agent-cme-research/      # Each agent = own repo
│   ├── src/agent.py
│   ├── Dockerfile               # Docker deploy
│   ├── langgraph.json           # Cloud deploy
│   └── pyproject.toml           # Depends on dhg-core
│
├── dhg-agent-curriculum/
├── dhg-agent-research/
└── ...
```

---

## Agent Template (Each Agent Repo)

```
dhg-agent-{name}/
├── src/
│   ├── __init__.py
│   └── agent.py                 # Main graph
├── Dockerfile                   # For Docker/K8s deploy
├── langgraph.json               # For LangSmith Cloud
├── pyproject.toml               # Dependencies
├── docker-compose.yml           # Local dev
└── README.md
```

---

## Migration Steps

### Phase 1: Extract Core Library
1. [ ] Create `dhg-core` repo
2. [ ] Move shared schemas to dhg_core/schemas
3. [ ] Create registry_client module
4. [ ] Publish to private PyPI or use git+ssh install

### Phase 2: Restructure Registry
1. [ ] Create `dhg-registry` repo
2. [ ] Move registry/ code to new repo
3. [ ] Update Dockerfile and compose

### Phase 3: Split Agents
1. [ ] Create agent template repo
2. [ ] Migrate CME Research agent first
3. [ ] Migrate remaining agents one by one
4. [ ] Update LangSmith to point to new repos

### Phase 4: CI/CD
1. [ ] GitHub Actions per repo
2. [ ] Automated Docker builds on push
3. [ ] LangSmith auto-deploy on tag

### Phase 5: Cleanup (swarchive)
1. [ ] Create cleanup.sh script
2. [ ] Set up cron job for 61-day purge
3. [ ] Document cleanup procedure

**Cleanup Rules:**
- Files marked for deletion → move to `swarchive/` in **same folder**
- Files stay in swarchive for 60 days (recovery period)
- Cron job runs daily, deletes files in any `swarchive/` folder under `~/` that are 61+ days old

**Cron job script (cleanup_swarchive.sh):**
```bash
#!/bin/bash
# Delete files in ~/*/swarchive or deeper that are 61+ days old
find ~/ -type d -name "swarchive" -exec find {} -type f -mtime +61 -delete \;
```

**Crontab entry:**
```cron
0 3 * * * /home/swebber64/scripts/cleanup_swarchive.sh
```

---

## Benefits

| Feature | Before | After |
|---------|--------|-------|
| **Versioning** | All agents same version | Independent |
| **Deploy** | Manual, mixed | Docker OR Cloud per agent |
| **Scale** | Rebuild all | Scale individual agents |
| **Testing** | Test everything | Test per agent |
| **Team** | Conflicts | Parallel development |
| **Cleanup** | Manual delete | 60-day archive + auto-purge |
