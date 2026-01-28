# DHG AI Factory Workflows Documentation

**Last Updated:** January 28, 2026

This document provides a comprehensive overview of all workflows, their purposes, improvement recommendations, and suggested additions.

---

## Table of Contents

1. [Workflow Overview](#workflow-overview)
2. [Detailed Workflow Documentation](#detailed-workflow-documentation)
3. [Improvement Recommendations](#improvement-recommendations)
4. [Suggested New Workflows](#suggested-new-workflows)
5. [Workflow Categories](#workflow-categories)

---

## Workflow Overview

| Workflow | Purpose | Status | Priority |
|----------|---------|--------|----------|
| `/pre-response` | Pre-flight checks before every response | ✅ Updated | Critical |
| `/session-start` | Session initialization and verification | ✅ Updated | Critical |
| `/agent-check` | Full project health review | ✅ Updated | High |
| `/data-infra-check` | Database/RAG infrastructure health | ✅ Updated | High |
| `/server-work` | Server-first development rules | ✅ Updated | Critical |
| `/debug-protocol` | Systematic debugging with hypothesis tracking | ⚠️ Needs Update | High |
| `/commit-flow` | Git commit workflow | ⚠️ Needs Update | Medium |
| `/git-github` | Git/GitHub operations | ⚠️ Needs Update | Medium |
| `/deploy-verify` | Post-deployment verification | ⚠️ Needs Update | Medium |
| `/infisical-secrets` | Secrets management | ⚠️ Needs Update | Medium |
| `/production-standards` | Code quality enforcement | ✅ OK | Medium |
| `/project-kickoff` | New project setup | ⚠️ Needs Update | Low |
| `/secret-safety` | Secret handling rules | ✅ OK | Critical |

---

## Detailed Workflow Documentation

### 1. `/pre-response` (MANDATORY)
**File:** `.agent/workflows/pre-response.md`

**Purpose:** Pre-flight checklist run before every AI response to ensure compliance with rules.

**What it does:**
- Enforces honesty protocol (no unverified claims)
- Confirms understanding of global rules (no placeholders, no truncation)
- Verifies Remote-SSH environment

**When to use:** Automatically, before every response.

**Key rules enforced:**
- No placeholders/TODOs
- Truth over helpfulness
- Debug discipline
- Pre-edit verification

---

### 2. `/session-start`
**File:** `.agent/workflows/session-start.md`

**Purpose:** Initialize a new working session with full environment verification.

**What it does:**
- Reads critical instruction files
- Verifies server environment (hostname check)
- Checks git branch and status
- Reviews recent commits
- Verifies Docker services health
- Checks critical agent endpoints

**When to use:** At the start of every new session.

---

### 3. `/agent-check`
**File:** `.agent/workflows/agent-check.md`

**Purpose:** Comprehensive project health review including agents, git, and infrastructure.

**What it does:**
- Docker container health (count healthy vs total)
- Agent endpoint health checks (7 agents, Orchestrator EOL'd)
- Git status and branch info
- Ollama model availability
- LibreChat status
- TODO.md review
- Agent implementation status (main.py count)
- Recent commits
- Disk and GPU usage

**When to use:** For full project status review or troubleshooting.

---

### 4. `/data-infra-check`
**File:** `.agent/workflows/data-infra-check.md`

**Purpose:** Verify all data infrastructure components are operational.

**What it does:**
- PostgreSQL databases (Registry, Infisical, Transcribe)
- MySQL databases (RAGFlow)
- Redis instances (5 total)
- RAG systems (RAGFlow, Dify)
- Elasticsearch cluster
- Vector databases
- Object storage (MinIO)
- Secrets management (Infisical)
- LLM infrastructure (Ollama)
- Cloudflare tunnel
- Public URLs

**When to use:** Before major deployments or when diagnosing data issues.

---

### 5. `/server-work`
**File:** `.agent/workflows/server-work.md`

**Purpose:** Document the Remote-SSH development environment.

**What it does:**
- Documents VS Code Remote-SSH setup
- Confirms file tools work directly on server
- Provides project path and branch info
- Session startup commands
- LibreChat endpoint documentation

**When to use:** Reference when unsure about environment.

---

### 6. `/debug-protocol`
**File:** `.agent/workflows/debug-protocol.md`

**Purpose:** Enforce systematic debugging with hypothesis tracking.

**What it does:**
- Phase 1: PAUSE (state problem)
- Phase 2: RESEARCH (gather evidence)
- Phase 3: HYPOTHESIZE (form causes)
- Phase 4: PLAN (requires approval)
- Phase 5: INVESTIGATE (execute plan)
- Phase 6: FIX (one attempt only)
- Phase 7: VERIFY (confirm fix)
- Phase 8: DOCUMENT (create report)

**Key rules:**
- ONE fix attempt per hypothesis
- No disguised retries
- Escalate after 3 failed hypotheses

**When to use:** For any non-trivial bug or issue.

---

### 7. `/commit-flow`
**File:** `.agent/workflows/commit-flow.md`

**Purpose:** Standardized git commit process.

**What it does:**
- Pre-commit checklist
- Branch verification
- Change review
- Staged file selection
- Conventional commit messages
- Push to remote

**Commit prefixes:** feat, fix, docs, chore, refactor, test

**When to use:** For every git commit.

---

### 8. `/git-github`
**File:** `.agent/workflows/git-github.md`

**Purpose:** Common git and GitHub operations reference.

**What it does:**
- Status check
- Commit and push
- Force push (after rebase)
- Sync with master (rebase)
- Branch management
- Undo mistakes
- Handle large files

**When to use:** Quick reference for git operations.

---

### 9. `/deploy-verify`
**File:** `.agent/workflows/deploy-verify.md`

**Purpose:** Post-deployment verification after Docker Compose changes.

**What it does:**
- Bring up services
- Wait for health checks (30s)
- Check container status
- Identify unhealthy containers
- Check logs for errors
- Verify critical endpoints

**When to use:** After any docker compose changes.

---

### 10. `/infisical-secrets`
**File:** `.agent/workflows/infisical-secrets.md`

**Purpose:** Secure secrets management guidelines.

**What it does:**
- Access instructions (UI only for login)
- Secret retrieval (CLI)
- Adding new secrets (UI only)
- Environment variable patterns
- Never-do list
- Masked output rules
- Current secrets inventory

**When to use:** When working with API keys or secrets.

---

### 11. `/production-standards`
**File:** `.agent/workflows/production-standards.md`

**Purpose:** Enforce code quality requirements.

**What it does:**
- Code quality rules (no stubs, no skeleton code)
- Workflow requirements
- Debugging protocol reminder
- Accountability statement

**When to use:** Acknowledgment at session start for critical work.

---

### 12. `/project-kickoff`
**File:** `.agent/workflows/project-kickoff.md`

**Purpose:** New project initialization.

**What it does:**
- Interview questions (14 items)
- Confirmation summary
- Create project structure
- Initialize git
- Create GitHub repo
- Antigravity config setup
- Standard files (README, .gitignore, TODO)
- Initial commit
- Optional: Registry integration, LangGraph scaffold

**When to use:** Starting a brand new project.

---

### 13. `/secret-safety`
**File:** `.agent/workflows/secret-safety.md`

**Purpose:** Prevent accidental secret exposure.

**What it does:**
- Absolute prohibitions (no cat .env, no printenv)
- Safe alternatives (masked output)
- Exposure response protocol
- Consequence reminder (GitHub auto-revokes)

**When to use:** Always (enforced by rules).

---

## Improvement Recommendations

### High Priority Updates Needed

| Workflow | Issue | Recommended Fix |
|----------|-------|-----------------|
| `/debug-protocol` | Still uses SSH wrapping | Update to Remote-SSH pattern |
| `/commit-flow` | Uses SSH, references old branch | Update to Remote-SSH, fix branch name |
| `/git-github` | Uses SSH wrapping | Update to Remote-SSH pattern |
| `/deploy-verify` | Uses SSH, references port 8011 | Update, remove Orchestrator check |
| `/infisical-secrets` | Uses SSH wrapping | Update to Remote-SSH pattern |
| `/project-kickoff` | Uses SSH wrapping | Update to Remote-SSH pattern |

### Enhancement Recommendations

| Workflow | Enhancement |
|----------|-------------|
| `/agent-check` | Add memory/CPU usage per container |
| `/data-infra-check` | Add CR (Conversation Registry) database check |
| `/debug-protocol` | Add LangSmith trace link integration |
| `/session-start` | Add check for pending PRs |
| `/deploy-verify` | Add rollback command if unhealthy |

---

## Suggested New Workflows

### 1. `/librechat-agent` (HIGH PRIORITY)
**Purpose:** Add or update a custom endpoint in LibreChat.

**Would include:**
- Edit `librechat.yaml`
- Restart LibreChat container
- Verify endpoint appears in UI
- Test basic functionality

### 2. `/ragflow-knowledge`
**Purpose:** Manage RAGFlow knowledge bases.

**Would include:**
- Create new knowledge base
- Upload documents
- Configure chunking/embedding
- Test retrieval
- Connect to agent

### 3. `/dify-workflow`
**Purpose:** Create or update Dify workflows.

**Would include:**
- Access Dify UI
- Create/edit workflow
- Configure RAG nodes
- Test workflow
- Export/backup

### 4. `/backup-restore`
**Purpose:** Database and config backup/restore.

**Would include:**
- Backup PostgreSQL databases
- Backup docker volumes
- Backup .env and config files
- Restore procedures
- Scheduled backup setup

### 5. `/agent-logs`
**Purpose:** Quick log viewing for specific agents.

**Would include:**
- View last N lines of agent logs
- Filter by error level
- Tail logs in real-time
- Search for specific patterns

### 6. `/model-management`
**Purpose:** Ollama model management.

**Would include:**
- List installed models
- Pull new models
- Remove unused models
- Check model memory usage
- Test model inference

### 7. `/cleanup`
**Purpose:** Project cleanup and maintenance.

**Would include:**
- Remove unused Docker images
- Clean build caches
- Archive old logs
- Check disk usage
- Remove orphan volumes

---

## Workflow Categories

### Critical (Read Every Session)
- `/pre-response`
- `/session-start`
- `/secret-safety`
- `/server-work`

### Health Checks
- `/agent-check`
- `/data-infra-check`
- `/deploy-verify`

### Git Operations
- `/commit-flow`
- `/git-github`

### Debugging
- `/debug-protocol`
- `/production-standards`

### Secrets & Security
- `/infisical-secrets`
- `/secret-safety`

### Project Setup
- `/project-kickoff`

---

## Next Steps

1. **Immediate:** Update 6 workflows for Remote-SSH (remove SSH wrapping)
2. **Short-term:** Create `/librechat-agent` workflow for agent integration
3. **Medium-term:** Add remaining suggested workflows based on usage
4. **Ongoing:** Keep workflows updated as infrastructure evolves
