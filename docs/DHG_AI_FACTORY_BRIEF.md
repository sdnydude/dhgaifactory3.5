# DHG AI Factory — Complete Project Brief for Claude Code

**Date:** April 19, 2026
**Server:** g700data1 (10.0.0.251), Ubuntu 24.04, Docker 29.1.5
**GPU:** NVIDIA RTX 5080 (16GB VRAM)
**RAM:** 64GB
**Disk:** 1.9TB root (12% used) + 3.6TB data disk mounted at `/mnt/4tb` (4% used, Docker Root Dir)
**Repo:** github.com/sdnydude/dhgaifactory3.5.git
**Owner:** Stephen Webber, CEO/Founder, Digital Harmony Group

**Changes since March 2, 2026 brief:** Gen 3 frontend is live (Next.js replacing React/Vite web-ui). LangGraph is production on LangGraph Cloud (local :2026 is dev-only). Auth/RBAC, LLManager Review Inbox, Inbox Document & Project Download (phase2v2), and the medkb RAG-as-a-Service have all shipped in the April wave. Dify, RAGFlow, and LibreChat are decommissioned. All 10 Criticals and most Majors from the March 3 audit are resolved; a fresh audit (`docs/AUDIT_REPORT_2026-04-19.md`) has identified 4 new Criticals introduced by the April feature waves.

---

## 1. What Is This Project?

DHG AI Factory is a **multi-agent platform** built by Digital Harmony Group on LangGraph that generates pharmaceutical-grade CME (Continuing Medical Education) grant documentation. The platform is also a general-purpose modular enterprise AI system — CME represents about 10% of DHG's revenue. CME compliance mode activates only when Stephen explicitly toggles it.

The platform evolved through three architectural generations:

1. **Gen 1 (LEGACY, decommissioned):** Monolithic Python orchestrator dispatching to per-agent Docker containers via WebSocket. Source retained in `agents/` for reference; all containers stopped with `restart: "no"`. Will not restart on reboot.
2. **Gen 2 (CURRENT, production):** 13 LangGraph agents + 3 orchestrator composition graphs = **17 total graphs** registered in `langgraph_workflows/dhg-agents-cloud/langgraph.json`. Production runs on **LangGraph Cloud** at `https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app` (auth via `x-api-key` + `LANGCHAIN_API_KEY`). A local LangGraph dev server on port 2026 exists for development only.
3. **Gen 3 (CURRENT, production frontend):** Next.js 16 + shadcn/ui + assistant-ui + CopilotKit + Refine + React Flow + Tremor. Connects to LangGraph Cloud via the langgraph-sdk and to the Registry API via a server-side proxy that forwards the Cloudflare Access JWT. The LLManager Review Inbox (`/inbox`) provides human-in-the-loop approval of interrupted LangGraph threads.

**Backend migration Gen 1 → Gen 2: complete.** **Frontend migration Gen 1 → Gen 3: complete.** Users reach LangGraph agents from `app.digitalharmonyai.com` via the Next.js frontend. The March "web-UI can't reach LangGraph" blocker is resolved.

---

## 2. Project Structure

```
/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/
├── .claude/                     # Claude Code config (CLAUDE.md, rules/, skills/, worktrees/)
├── .codegraph/                  # CodeGraph semantic index
├── agents/                      # Gen 1 legacy source (DECOMMISSIONED, kept for reference)
│   ├── orchestrator/            # Legacy WebSocket orchestrator
│   ├── medical-llm/             # STOPPED, restart:"no"
│   ├── research/                # STOPPED, restart:"no"
│   ├── competitor-intel/        # STOPPED, restart:"no"
│   ├── visuals/                 # STOPPED, restart:"no"
│   └── ...                      # curriculum, outcomes, qa-compliance (already removed)
├── langgraph_workflows/
│   ├── dhg-agents-cloud/        # Gen 2 LangGraph agents (THE CURRENT SYSTEM)
│   │   ├── src/
│   │   │   ├── needs_assessment_agent.py      (1110 lines)
│   │   │   ├── research_agent.py              (1160 lines)
│   │   │   ├── clinical_practice_agent.py     (864 lines)
│   │   │   ├── gap_analysis_agent.py          (775 lines)
│   │   │   ├── learning_objectives_agent.py   (894 lines)
│   │   │   ├── curriculum_design_agent.py     (1045 lines)
│   │   │   ├── research_protocol_agent.py     (977 lines)
│   │   │   ├── marketing_plan_agent.py        (867 lines)
│   │   │   ├── grant_writer_agent.py          (926 lines)
│   │   │   ├── prose_quality_agent.py         (672 lines)
│   │   │   ├── compliance_review_agent.py     (436 lines)
│   │   │   ├── citation_checker_agent.py      (~450 lines, NEW Apr)
│   │   │   ├── registry_agent.py              (~290 lines, NEW Apr — gateway)
│   │   │   ├── intake_prefill_agent.py        (NEW)
│   │   │   ├── orchestrator.py                (1700+ lines — 3 composition graphs)
│   │   │   ├── tracing.py                     (OTel @traced_node — 85 decorators across 11 agents)
│   │   │   ├── drive_sync.py                  (enqueue Google Drive sync from orchestrator milestones)
│   │   │   └── llm_factory.py                 (partial — used by medkb-style paths only)
│   │   ├── tests/                             (5 test files)
│   │   ├── langgraph.json                     (17 graphs registered)
│   │   ├── runtime.env                        (non-secret config, docs-only for LangGraph Cloud)
│   │   └── docker-compose.yml                 (LOCAL DEV ONLY — port 2026)
│   └── Archive/                               (legacy research-agent — still present, scheduled for deletion)
├── registry/                    # FastAPI data registry (port 8011)
│   ├── api.py                   # Main app — CORS, middleware, lifespan, /healthz, /metrics
│   ├── auth.py                  # Cloudflare JWT validation, FastAPI dependencies (NEW Apr)
│   ├── security_endpoints.py    # RBAC admin + users/me (NEW Apr, /api/v1/security/*)
│   ├── security_schemas.py      # (NEW Apr)
│   ├── cme_endpoints.py         # CME project CRUD, agent output storage, review workflow
│   ├── agent_endpoints.py       # Agent registration, heartbeat
│   ├── claude_endpoints.py      # Claude import
│   ├── antigravity_endpoints.py # Antigravity session import
│   ├── research_endpoints.py
│   ├── import_api.py            # Bulk importers
│   ├── importers/
│   │   ├── markdown_parser.py
│   │   └── official_export_parser.py
│   ├── search_api.py            # Full-text + pgvector similarity
│   ├── export_endpoints.py      # Phase2v2 download/bundle/drive-sync (NEW Apr, /api/cme/export/*)
│   ├── export_service.py        # HMAC print-token mint + pdf-renderer dispatch (NEW Apr)
│   ├── export_signing.py        # HMAC token signing/verification (NEW Apr)
│   ├── export_schemas.py        # (NEW Apr)
│   ├── project_schemas.py       # (NEW Apr)
│   ├── projects_endpoints.py
│   ├── frontend_specs_endpoints.py
│   ├── inference_endpoints.py
│   ├── dev_changelog_endpoints.py
│   ├── webhook_endpoints.py     # /webhooks/alertmanager handler
│   ├── incident_endpoints.py
│   ├── models.py                # SQLAlchemy models (64 tables)
│   ├── schemas.py               # Pydantic DTOs
│   ├── database.py              # Sync engine (pool_size=10, max_overflow=20, pool_pre_ping)
│   ├── websocket_manager.py     # DEAD CODE — stub, not mounted (see audit MAJ-6)
│   ├── notification_service.py
│   ├── timeout_handler.py
│   ├── test_*.py                # 12 test files, 227 tests (NEW Apr)
│   └── alembic/versions/        # Migrations 001 → 011
├── services/
│   ├── medkb/                   # NEW Apr — RAG-as-a-Service for medical knowledge
│   │   ├── src/medkb/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── auth.py          # (weak — see audit MAJ-2)
│   │   │   ├── graph/           # LangGraph nodes: retrieve_fan, redact, analyze_query,
│   │   │   │                    #  rerank, format_cite, grade, rewrite, emit_feedback, etc.
│   │   │   ├── retriever/       # PgVectorRetriever with dual-embedding support
│   │   │   ├── endpoints/       # /v1/query, /v1/retrieve, corpora CRUD
│   │   │   └── llm_factory.py   # init_chat_model (Ollama + Claude)
│   │   ├── tests/               # 21 test files, 46 tests
│   │   └── migrations/
│   ├── pdf-renderer/            # NEW Apr — Playwright PDF renderer + bundler + Drive sync worker
│   │   ├── main.py              # FastAPI service (internal network only, port 8014)
│   │   ├── renderer.py          # Playwright render helper, waits for [data-print-ready=true]
│   │   ├── bundler.py           # md-only project bundler (ZIP with manifest.json)
│   │   ├── drive_client.py      # Google Drive service-account client
│   │   ├── drive_sync.py        # Drive sync action with manifest reconciliation
│   │   ├── worker.py            # Job claim loop (FOR UPDATE — see audit MAJ-5)
│   │   └── db.py
│   ├── session-logger/          # Session logging (port 8009)
│   ├── logo-maker/              # Logo generation (port 8012) — CORS wildcard issue, see audit SEC-3
│   └── vs-engine/               # Verbalized Sampling Engine (port 8013, Cloudflare-tunneled)
├── frontend/                    # Next.js 16 production frontend (replaces legacy web-ui)
│   ├── src/
│   │   ├── app/
│   │   │   ├── api/registry/[...path]/route.ts     # Registry proxy (binary-safe, CF JWT forward)
│   │   │   ├── api/langgraph/[...path]/route.ts    # LangGraph Cloud proxy
│   │   │   ├── api/copilotkit/route.ts             # AG-UI / CopilotKit bridge
│   │   │   ├── api/auth/me/route.ts
│   │   │   ├── print/cme/document/                 # HMAC-gated print route
│   │   │   ├── inbox/page.tsx                      # LLManager Review Inbox
│   │   │   ├── dashboards/page.tsx                 # Monitoring links
│   │   │   ├── agents/page.tsx                     # AgentsLibrary
│   │   │   └── page.tsx                            # Root
│   │   ├── middleware.ts        # Cloudflare JWT route guard (SECURITY_DEV_MODE bypass)
│   │   ├── lib/
│   │   │   ├── permissions.ts   # Role-based route visibility
│   │   │   ├── printTokens.ts   # Edge-Runtime HMAC verifier
│   │   │   ├── inboxApi.ts      # LangGraph SDK wrapper
│   │   │   ├── filesApi.ts      # Export/download client
│   │   │   └── exportApi.ts
│   │   ├── stores/
│   │   │   ├── session-store.ts       # Zustand (memory-only, no localStorage)
│   │   │   ├── review-store.ts        # Inbox state
│   │   │   ├── files-tab-store.ts     # Files tab (projects/docs/preview)
│   │   │   └── downloads-store.ts     # Downloads tray
│   │   ├── hooks/
│   │   │   ├── use-session.ts
│   │   │   └── use-download-polling.ts
│   │   ├── components/
│   │   │   ├── review/                # Master-detail inbox (inbox-master-detail, review-panel,
│   │   │   │                          #   reflection-panel, metrics-bar, decision-bar, document-viewer)
│   │   │   ├── downloads/             # Downloads tray
│   │   │   ├── agents-library/        # Agents Library (toolbar, grid, list, table, slide-over)
│   │   │   └── nav/                   # Role-aware sidebar (Work/Observe/Manage sections)
│   │   └── ...
│   ├── e2e/                     # Playwright E2E tests (2+ specs)
│   ├── package.json             # Next 16, shadcn/ui, assistant-ui, CopilotKit, Zustand, langgraph-sdk
│   ├── next.config.ts
│   └── tsconfig.json
├── observability/               # Full observability stack (configs)
│   ├── prometheus/              # 6 scrape targets
│   ├── grafana/                 # Provisioned dashboards (core golden signals, Docker overview)
│   ├── loki/                    # Log aggregation
│   ├── promtail/                # Docker log scraper
│   ├── tempo/                   # Distributed tracing (OTel gRPC :4317, HTTP :4318)
│   └── alertmanager/            # Alert routing (webhook to registry-api)
├── scripts/                     # Import scripts, sync utilities
├── docs/
│   ├── CLAUDE.md                # Canonical architecture source-of-truth (in project root)
│   ├── Architecture.md
│   ├── AUTH_AND_RBAC.md
│   ├── AUDIT_REPORT_2026-04-19.md   # NEW — this week's audit
│   ├── BURNDOWN.md
│   ├── CLOUDFLARE_TUNNEL_SETUP.md
│   ├── LLMANAGER_REVIEW.md
│   ├── OBSERVABILITY_RUNBOOK.md
│   ├── REGISTRY_API.md
│   ├── FRONTEND.md
│   ├── resolved-issues.md
│   ├── TODO.md
│   ├── superpowers/plans/       # Active planning docs
│   ├── superpowers/specs/       # Design specs
│   └── archive/                 # 55+ historical docs
├── DHG-CME-12-Agent-Docs/       # 28 files, 12-agent system specs
├── .github/workflows/ci.yml     # GitHub Actions: lint-python, lint-js, test-registry (NEW Apr)
├── docker-compose.yml           # Main compose — DHG stack
├── docker-compose.override.yml  # Override — registry-api, observability, session-logger, logo-maker,
│                                #   medkb stack, pdf-renderer, frontend, remediator
├── pyrightconfig.json           # Python LSP config
└── .env                         # Secrets (gitignored)
```

---

## 3. Docker Infrastructure — Complete Container Inventory

### 3.1 Running Containers (as of 2026-04-19)

#### DHG AI Factory Core Stack
| Container | Port | Image | Health | Notes |
|-----------|------|-------|--------|-------|
| dhg-registry-db | 5432 | pgvector/pgvector:pg15 | healthy | 64 tables, migrations 001–011 |
| dhg-registry-api | 8011 → 8000 | custom | healthy | FastAPI, Prometheus /metrics, Apr auth/RBAC |
| dhg-frontend | 3000 | custom (Next.js) | healthy | Production frontend — replaces web-ui |
| dhg-ollama | 11434 | ollama/ollama:latest | healthy | llama3.1:8b, qwen3:14b, nomic-embed-text (audit MIN-4: unpinned) |
| dhg-session-logger | 8009 | custom | healthy | Uses Ollama for session embeddings |
| dhg-logo-maker | 8012 | custom | healthy | ⚠️ audit SEC-3: CORS wildcard |
| dhg-audio-agent | 8101 | custom | healthy | |
| dhg-audio-postgres | 5434 | postgres | healthy | Dedicated DB |
| dhg-pdf-renderer | internal 8014 | custom | healthy | Playwright + bundler + Drive worker |
| dhg-remediator | — | custom | no healthcheck | ⚠️ audit MIN-7: dry-run=false default |

#### medkb RAG-as-a-Service (NEW April)
| Container | Port | Image | Health | Notes |
|-----------|------|-------|--------|-------|
| dhg-medkb-db | 5435 → 5432 | pgvector/pgvector:pg15 | healthy | Separate knowledge corpus DB |
| dhg-medkb-cache | 6381 → 6379 | redis:7 | healthy | 4GB LRU query/embedding cache |
| dhg-medkb-api | 8015 | custom | healthy | RAG endpoints: /v1/query, /v1/retrieve |
| dhg-medkb-ingestor | — | custom | ⚠️ unhealthy | Phase 5 stub — audit MAJ-1: healthcheck contradicts command |

#### LangGraph Dev Server (LOCAL DEV ONLY)
| Container | Port | Image | Health | Notes |
|-----------|------|-------|--------|-------|
| dhg-cme-research-agent | 2026 | custom | Exited (0), 3 days ago | ⚠️ audit MAJ-12: orphaned on disk |

Production LangGraph is on **LangGraph Cloud** — no local container runs it.

#### Observability Stack (NEW/UPGRADED April)
| Container | Port | Image | Health | Notes |
|-----------|------|-------|--------|-------|
| dhg-prometheus | 9090 | prom/prometheus:v2.48.0 | healthy | 6 scrape targets, all UP |
| dhg-grafana | 3001 → 3000 | grafana/grafana:10.2.0 | healthy | ⚠️ audit SEC-2: admin password hardcoded |
| dhg-loki | 3100 | grafana/loki:2.9.0 | healthy | Now ingesting via Promtail (resolved March BUG-10) |
| dhg-tempo | 3200, 4317, 4318 | grafana/tempo | healthy | Distributed tracing (NEW Apr) |
| dhg-promtail | — | grafana/promtail | healthy | Docker container log shipping (NEW Apr) |
| dhg-alertmanager | 9093 | prom/alertmanager | healthy | Webhook to registry-api (NEW Apr) |
| dhg-cadvisor | 8080 | gcr.io/cadvisor/cadvisor:v0.51.0 | healthy | |
| dhg-node-exporter | 9100 | prom/node-exporter | healthy | |
| dhg-postgres-exporter | 9187 | prometheuscommunity/postgres-exporter | healthy | |

#### Transcribe Pipeline (separate stack, independent)
| Container | Port | Notes |
|-----------|------|-------|
| dhg-transcribe | 8200 | Main API, GPU-accelerated |
| dhg-preprocessor, dhg-nlp-processor, dhg-nlp-enrichment, dhg-qc-service, dhg-api-server | 8203-8206, 8210 | Pipeline stages |
| dhg-transcribe-db | 5433 | PostgreSQL |
| dhg-transcribe-minio | 9000/9001 | Object storage |
| dhg-transcribe-qdrant | 6333/6334 | Vector DB |
| dhg-transcribe-redis | 6380 | Cache |
| dhg-transcribe-worker, dhg-cognitive | — | Background, on `onyx_default` network |

#### Third-Party Stacks
| Stack | Status | Notes |
|-------|--------|-------|
| Dify | ❌ DECOMMISSIONED Apr 6 | Zero usage, worker crash-looping; containers/volumes/DB/dirs deleted |
| RAGFlow | ❌ DECOMMISSIONED Apr 6 | Zero usage; all containers/volumes/dirs deleted |
| LibreChat | ❌ DECOMMISSIONED | Replaced by assistant-ui in the Next.js frontend |
| Infisical | ✅ Running | 5 containers (backend, postgres, 2× redis, dev-redis); port 8089 |
| pgAdmin | ✅ Running | Port 5050 |

### 3.2 Docker Networks
| Network | Purpose | Key Members |
|---------|---------|-------------|
| dhgaifactory35_dhg-network | Main DHG stack | registry, agents, frontend, observability, medkb, pdf-renderer |
| dhg-agents-cloud_default | Local LangGraph dev | dhg-cme-research-agent (Exited) |
| dhg-transcribe_default | Transcribe pipeline | All transcribe-* services |
| dhgaifactory35_default | Leftover network | Only `dhg-logo-maker` — ⚠️ audit MIN-5: wrong network |
| dhg-network | Leftover network | Only `pgadmin` — ⚠️ audit MIN-6 |
| onyx_default | Cross-stack | dhg-cognitive (separate stack) |

### 3.3 Docker Compose Files
| File | Location | Services |
|------|----------|----------|
| docker-compose.yml | Project root | Legacy agents (dormant), registry-db, ollama, medkb stack |
| docker-compose.override.yml | Project root | registry-api, session-logger, logo-maker, observability, pdf-renderer, frontend, remediator |
| docker-compose.yml | langgraph_workflows/dhg-agents-cloud/ | LOCAL DEV ONLY LangGraph Server |
| docker-compose.yml | services/medkb/ | medkb RAG service |

---

## 4. Database Schema

**PostgreSQL 15 + pgvector** — **64 tables** in `dhg_registry` (up from 57 in March). A separate `medkb` database on `dhg-medkb-db:5435` stores the knowledge corpus.

### Core Tables (unchanged from March)
agents, agent_heartbeats, agent_memory, conversations, messages, events, documents, artifacts.

### CME-Specific Tables
cme_projects, cme_agent_outputs, cme_lectures, cme_segments, cme_review_assignments, cme_reviewer_config, **cme_source_references** (Apr, with verification_status columns), **cme_documents** (Apr).

### Import/Sync Tables (unchanged)
claude_conversations, claude_messages, chatgpt_conversations, chatgpt_messages, gemini_conversations, gemini_messages, antigravity_chats, antigravity_messages, antigravity_artifacts, antigravity_files, planning_documents, planning_embeddings.

### Auth & RBAC (NEW April — migration 004)
| Table | Purpose |
|-------|---------|
| security_users | Cloudflare-authenticated user records |
| security_roles | 5 seeded: admin, operations, finance, editor, viewer |
| security_user_roles | User → role mapping |
| security_project_access | Per-project access grants |
| security_audit_log | Audit trail (currently only RBAC admin writes — audit CRIT-1) |

### Export Pipeline (NEW April — migrations 009 + 010)
| Table | Purpose |
|-------|---------|
| download_jobs | Scope ∈ {document, project_bundle, drive_sync} with CHECK constraint; project_id, drive_file_id, drive_folder_id, drive_mime_type, selected_document_ids |

### LangGraph Checkpointing (unchanged)
checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations, langgraph_checkpoints, langgraph_writes.

### Knowledge/Research (unchanged)
knowledge_items, knowledge_entities, knowledge_relationships, research_requests, references, reference_vectors, learning_objectives, outcomes, assessments.

### Alembic Migrations
- `001_initial_schema.py`
- `002_add_claude_data.py`
- `003_add_cme_review.py`
- `004_add_security_rbac.py` (NEW Apr)
- `005_add_verification_status_to_cme_source_references.py` (NEW Apr)
- `006` → `008` (incremental, Apr)
- `009_add_download_jobs.py` (NEW Apr)
- `010_extend_download_jobs_v2.py` (NEW Apr — project bundles + Drive sync)
- `011` (pending — recommended by audit MAJ-5 for pdf-renderer retry columns)

Alembic chain verified linear, no collisions.

---

## 5. LangGraph Agent Architecture

### 5.1 The 17 Registered Graphs

**13 Individual Agent Graphs:**
| Agent | File | Lines | Key Pattern |
|-------|------|-------|-------------|
| Needs Assessment | needs_assessment_agent.py | 1110 | 10-node sequential, cold open framework, 3100+ word validation |
| Research | research_agent.py | 1160 | Literature/PubMed queries, 30+ sources |
| Clinical Practice | clinical_practice_agent.py | 864 | Barrier identification, standard-of-care analysis |
| Gap Analysis | gap_analysis_agent.py | 775 | 5+ evidence-based gaps, quantification |
| Learning Objectives | learning_objectives_agent.py | 894 | Moore's Expanded Framework mapping |
| Curriculum Design | curriculum_design_agent.py | 1045 | Educational design + innovation section |
| Research Protocol | research_protocol_agent.py | 977 | IRB-ready outcomes protocol |
| Marketing Plan | marketing_plan_agent.py | 867 | Audience strategy + channel budget |
| Grant Writer | grant_writer_agent.py | 926 | Full package assembly |
| Prose Quality | prose_quality_agent.py | 672 | De-AI-ification scoring, banned pattern detection |
| Compliance Review | compliance_review_agent.py | 436 | ACCME verification |
| **Citation Checker** (NEW Apr) | citation_checker_agent.py | ~450 | PubMed verification; outputs `registry_request` for gateway |
| **Registry Agent** (NEW Apr) | registry_agent.py | ~290 | Gateway for all agent writes to Registry API; SHA-256 idempotency, dead letter queue |

Plus `intake_prefill_agent.py` (standalone, registered in `langgraph.json`).

**3 Orchestrator Composition Graphs (in orchestrator.py):**
| Recipe | Export | Pattern |
|--------|--------|---------|
| needs_package | `needs_graph` | Research + Clinical parallel → Gap → LO → Needs → Prose QA Pass 1 → Human Review |
| curriculum_package | `curriculum_graph` | Needs Package + Curriculum + Protocol + Marketing parallel → Human Review |
| grant_package | `grant_graph` | Full 11 agents, Prose QA 2 passes, Compliance gate, Human Review |

### 5.2 LangGraph Cloud (Production)
- **URL:** `https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app`
- **Auth:** `x-api-key` header with `LANGCHAIN_API_KEY`
- **Deployment config:** LangSmith Secrets UI owns production env (API keys, `SKIP_HUMAN_REVIEW`, etc.)
- **Dual tracing:** LangSmith (`@traceable`) + OpenTelemetry (`@traced_node` via `tracing.py`) on every graph node — 85 decorators total
- **Checkpointing:** PostgresSaver (production persistence in Cloud-managed DB)

### 5.3 Local LangGraph Dev Server (dev-only)
- Container: `dhg-cme-research-agent` (Exited 3 days ago; orphaned — audit MAJ-12)
- Port 2026
- Network: `dhg-agents-cloud_default`
- Env: `LANGCHAIN_TRACING_V2=true`, `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- ⚠️ `.env.example:47` still teaches `AI_FACTORY_REGISTRY_URL=http://localhost:8500` — audit MAJ-11

### 5.4 Known Risks (from `docs/AUDIT_REPORT_2026-04-19.md`)
- **CRIT-3:** `SKIP_HUMAN_REVIEW` defaults to `"true"` in `orchestrator.py:90` — silent auto-approve if LangSmith Secrets UI misses the override.
- **CRIT-4:** `intake_prefill_agent.py:14` still imports `TypedDict` from `typing` (should be `typing_extensions`).
- **MAJ-3:** 8 bare `except:` in grant_writer + compliance_review swallow `asyncio.CancelledError`.
- **MAJ-4:** All 11 content agents hardcode Claude model IDs — violates LLM-agnostic strategy in `MEMORY.md`.
- **MAJ-13:** Only 5/13 agents have tests.

---

## 6. Registry API Architecture

FastAPI service exposed on port 8011 (→ container :8000). Modular endpoint files:

| File | Purpose | Notes |
|------|---------|-------|
| api.py | Main app, health, metrics, CORS, lifespan | CORS origins locked to `app.digitalharmonyai.com` + localhost (March C3 resolved); `allow_headers=["*"]` remains (audit MAJ-14) |
| auth.py | **Cloudflare JWT validation + dependencies** (NEW Apr) | JWKS cache, audience check, `get_current_user`, `require_permission`, `require_role` |
| security_endpoints.py | **RBAC admin + users/me** (NEW Apr, `/api/v1/security/*`) | Only router with auth dependencies actually applied — audit CRIT-1 |
| cme_endpoints.py | CME CRUD, agent output, review workflow | No auth applied — audit CRIT-1 |
| agent_endpoints.py | Agent registration, heartbeat, capabilities | |
| claude_endpoints.py, antigravity_endpoints.py, research_endpoints.py | Import APIs | |
| import_api.py, importers/*.py | Bulk import + markdown/official parsers | ⚠️ bare `except: pass` (audit SEC-8) |
| search_api.py | Full-text + pgvector similarity | ⚠️ f-string table name at :179 (allowlist-safe but audit MAJ-10) |
| **export_endpoints.py** (NEW Apr) | Phase2v2 download/bundle/drive-sync | ⚠️ comment: "Auth handled by Cloudflare Access" |
| **export_service.py** (NEW Apr) | HMAC token mint + pdf-renderer dispatch | |
| **export_signing.py** (NEW Apr) | HMAC signing (`hmac.compare_digest`, TTL enforced) | ⚠️ no rotation path (audit SEC-6) |
| **export_schemas.py, project_schemas.py** (NEW Apr) | Pydantic schemas | |
| **projects_endpoints.py, frontend_specs_endpoints.py, inference_endpoints.py, dev_changelog_endpoints.py, webhook_endpoints.py, incident_endpoints.py** | New endpoint surfaces | |
| notification_service.py | Email/webhook dispatch | |
| websocket_manager.py | **DEAD CODE** — stub ships in image (audit MAJ-6) | Not mounted in api.py |
| timeout_handler.py | Request timeout middleware | |

**Prometheus metrics at `/metrics`:**
- `registry_db_read_latency_ms` (histogram)
- `registry_write_operations` (counter by operation)
- `registry_read_operations` (counter by operation)
- `registry_errors` (counter by error_type)
- `registry_db_connections` (gauge)

**Connection pool:** `pool_pre_ping=True, pool_size=10, max_overflow=20`. Missing `pool_recycle=1800` (audit MIN-14).

**Test coverage:** 12 test files, 227 tests. CI runs pytest against a real Postgres 15 + pgvector container.

---

## 7. Frontend Architecture (NEW — replaces legacy web-UI)

**Legacy `web-ui/` directory is DECOMMISSIONED.** The production frontend is the Next.js 16 app under `frontend/`.

### 7.1 Stack
| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16 (App Router, Edge Runtime for middleware) |
| Design system | shadcn/ui |
| Chat UI | assistant-ui with LangGraph starter |
| Agent bridge | CopilotKit + AG-UI protocol (@ag-ui/langgraph package) |
| Admin console | Refine (FastAPI data providers) |
| Workflow editor | React Flow |
| Monitoring dashboards | Tremor |
| State | Zustand stores (session, review, files-tab, downloads) |
| LangGraph client | langgraph-sdk (points to Cloud URL in prod) |

### 7.2 Route Map
- `/` — root landing
- `/inbox` — **LLManager Review Inbox** (master-detail: pending threads list + document + AI reflection panel, auto-refresh 30s)
- `/inbox` → Files tab — **Inbox Document & Project Download** (phase2v2): browse projects, multi-select documents, enqueue bundle / Drive sync, downloads tray
- `/agents` — Agents Library (grid/list/table)
- `/dashboards` — Monitoring tiles (Grafana, Prometheus, Tempo, Alertmanager) — ⚠️ audit MAJ-7: hardcoded LAN IPs
- `/admin` — Admin console (RBAC-gated)
- `/api/registry/[...path]` — Registry proxy (binary-safe via `arrayBuffer()`, forwards Cloudflare JWT)
- `/api/langgraph/[...path]` — LangGraph Cloud proxy (server-side `LANGCHAIN_API_KEY`)
- `/api/copilotkit` — AG-UI bridge
- `/api/auth/me` — Session fetch
- `/print/cme/document` — HMAC-gated print route (middleware bypass gated by token only)

### 7.3 Auth Flow
1. Cloudflare Access validates user at edge, issues `CF_Authorization` httpOnly cookie + `Cf-Access-Jwt-Assertion` header.
2. Next.js `middleware.ts` validates JWT against JWKS, extracts identity.
3. Session-store (Zustand, in-memory) hydrates from `/api/auth/me`.
4. `/api/registry/[...path]` proxy forwards `Cf-Access-Jwt-Assertion` to registry API.
5. Registry API `auth.py` validates JWT, enforces RBAC — **audit CRIT-1: only applied on `/api/v1/security/*`**.

### 7.4 Known Risks (from audit)
- **MAJ-8:** `NEXT_PUBLIC_SECURITY_DEV_MODE=true` at build time ships a hardcoded admin `DEV_USER` to every visitor's browser — single env flip = full RBAC bypass.
- **MAJ-7:** `/dashboards/page.tsx` hardcodes `10.0.0.251` for Grafana/Prometheus/Tempo/Alertmanager.
- **SEC-4:** No CSP, X-Frame-Options, HSTS, or Referrer-Policy in `next.config.ts`.
- **SEC-5:** 19 npm vulns (7 high) via `@copilotkit/react-ui` transitive deps.
- Binary proxy fix (`b736357` — `arrayBuffer()` for PDF/zip) **is preserved**.

### 7.5 E2E Tests
Playwright specs under `frontend/e2e/`:
- `inbox-document-download.spec.ts`
- `inbox-project-bundle.spec.ts` — 5-test suite covering projects list, documents list, bundle round-trip with ZIP + manifest verification, 404/409 error cases

---

## 8. Observability Stack

### Current State (April 2026 — significantly upgraded from March)
| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| Prometheus | v2.48.0 | healthy | 6 scrape targets, all UP |
| Grafana | 10.2.0 | healthy | Dashboards: core golden signals, Docker overview; ⚠️ audit SEC-2 admin password |
| Loki | 2.9.0 | healthy | **Now ingesting** (March BUG-10 resolved) |
| Tempo | (grafana/tempo) | healthy | NEW Apr — distributed tracing (OTel gRPC :4317, HTTP :4318) |
| Promtail | (grafana/promtail) | healthy | NEW Apr — Docker container log shipping from `/mnt/4tb/docker/containers` |
| Alertmanager | (prom/alertmanager) | healthy | NEW Apr — webhook to registry-api `/webhooks/alertmanager` (audit SEC-7: unauthenticated) |
| cAdvisor | v0.51.0 | healthy | |
| Node Exporter | v1.7.0 | healthy | |
| Postgres Exporter | v0.15.0 | healthy | |

### Prometheus Scrape Targets (6, all UP)
1. `prometheus` — self
2. `registry-api` — /metrics, 10s
3. `postgres-exporter` — 30s
4. `node-exporter` — 15s
5. `cadvisor` — 15s
6. LangGraph agents — via remote tracing pipeline (OTel → Tempo, not scraped directly)

### Resolved March Gaps
- ✅ Log collection: Promtail shipping to Loki (fixed volume mount at `/mnt/4tb/docker`)
- ✅ Alerting: Alertmanager deployed
- ✅ Distributed tracing: Tempo deployed, 85 `@traced_node` decorators across all 11 content agents via `tracing.py`
- ✅ Healthchecks added to all containers (via `bash /dev/tcp` for Promtail/Ollama, commit `8b2d05d`)

### Remaining Gaps
- Static targets (no Docker Service Discovery) — still March-era config
- LangGraph Server `/metrics` not scraped (LangGraph Cloud handles its own metrics)
- Observability of the observers: `dhg-remediator` has no healthcheck (audit MIN-7); `dhg-medkb-ingestor` healthcheck is misconfigured (audit MAJ-1)

---

## 9. Known Bugs and Challenges

### Resolved Since March
| March bug | Status | Resolution |
|-----------|--------|------------|
| BUG-1 Web-UI can't reach LangGraph | ✅ RESOLVED | Legacy web-UI decommissioned; Next.js `frontend/` uses langgraph-sdk to LangGraph Cloud |
| BUG-2 LangGraph network isolation | ✅ MITIGATED | Production runs in LangGraph Cloud; local dev still uses `host.docker.internal` |
| BUG-3 Registry URL on port 8500 | ✅ MOSTLY RESOLVED | Compose file fixed; `.env.example` still wrong (audit MAJ-11) |
| BUG-4 Stale root-level files | ✅ RESOLVED | `MainLayout.jsx`, `main.py`, proxy scripts removed |
| BUG-5 9 backup files | ✅ RESOLVED | Zero `.bak`/`.backup` files remain |
| BUG-6 Legacy `dhg-ai-factory-ui/` | ✅ RESOLVED | Deleted (Mac resource forks only remain in worktrees) |
| BUG-7 No CI/CD | ✅ RESOLVED | `.github/workflows/ci.yml` runs lint + pytest |
| BUG-8 Minimal test coverage | ⚠️ IMPROVED | 12 registry + 21 medkb + 5 langgraph + 2 frontend e2e (audit MAJ-13: 8/13 agents still untested) |
| BUG-9 Doc sprawl | ✅ IMPROVED | 55+ files archived to `docs/archive/`; CLAUDE.md is canonical |
| BUG-10 Loki no log ingestion | ✅ RESOLVED | Promtail shipping Docker logs |

### New / Open (from `docs/AUDIT_REPORT_2026-04-19.md`)

#### 🔴 Critical
- **CRIT-1:** Backend auth (`Depends(get_current_user)`) applied to `/api/v1/security/*` only — ~60 business endpoints rely on Cloudflare Access as the sole gate. No audit trail for business actions.
- **CRIT-2:** Postgres password `weenie64` committed to `docker-compose.override.yml` (4 lines) + `registry/database.py:30` default + 3 legacy `agents/orchestrator/*.py`. Repo is public on GitHub.
- **CRIT-3:** `SKIP_HUMAN_REVIEW` defaults to `"true"` at `orchestrator.py:90` — silent CME auto-approve if Secrets UI misses the override.
- **CRIT-4:** `intake_prefill_agent.py:14` still imports `TypedDict` from `typing` (missed April 8 sweep).

#### 🟡 Major (selected — 14 total in audit)
- **MAJ-1:** `dhg-medkb-ingestor` healthcheck contradicts its stub command → permanent unhealthy → alert fatigue.
- **MAJ-2:** medkb `resolve_caller()` echoes any `x-medkb-key` header with no validation — `/v1/query` and `/v1/retrieve` on port 8015 fully open on Docker network.
- **MAJ-3:** 6 bare `except:` in `grant_writer_agent.py` + 2 in `compliance_review_agent.py` swallow `asyncio.CancelledError` → timeout cancellation hangs.
- **MAJ-4:** All 11 agents hardcode Claude model IDs — breaks the LLM-agnostic promise for the RTX 5090 + Nemotron migration.
- **MAJ-5:** pdf-renderer worker uses plain `FOR UPDATE` not `SKIP LOCKED` (CLAUDE.md is wrong about current state); no retry logic, no DLQ.
- **MAJ-6:** `registry/websocket_manager.py` dead-code stub ships in the image.
- **MAJ-7:** `/dashboards/page.tsx` hardcodes `10.0.0.251` for monitoring tile URLs.
- **MAJ-8:** `NEXT_PUBLIC_SECURITY_DEV_MODE` is a client-bundle bypass landmine.
- **MAJ-9:** pdf-renderer imports `registry/models.py` — cross-service Python coupling.
- **MAJ-10:** `session-logger` uses hardcoded bridge gateway `172.17.0.1` for Ollama instead of DNS.
- **MAJ-11:** `.env.example` still teaches wrong registry URL (port 8500).
- **MAJ-12:** Legacy `dhg-cme-research-agent` container still on disk on port 2026.
- **MAJ-13:** 8/13 LangGraph agents have zero tests.
- **MAJ-14:** `allow_headers=["*"]` + `allow_credentials=True` in registry CORS.

#### 🟢 Minor / Security (11 MIN + 7 SEC — see audit report for full list)

---

## 10. Environment Variables (Key Names Only)

The `.env` file contains secrets:
- **DB:** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DB_PASSWORD`
- **LLM API keys:** `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `PERPLEXITY_API_KEY`
- **LangChain:** `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2`
- **PubMed:** `PUBMED_API_KEY`, `NCBI_API_KEY`
- **Infisical:** `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`

**NEW since March:**
- **Auth:** `SECURITY_DEV_MODE` (backend bypass), `NEXT_PUBLIC_SECURITY_DEV_MODE` (⚠️ audit MAJ-8), Cloudflare JWKS URL
- **Exports:** `EXPORT_SIGNING_SECRET` (HMAC for print tokens — ⚠️ audit SEC-6 no rotation)
- **medkb:** `MEDKB_API_KEY` (not yet enforced — audit MAJ-2), `OLLAMA_BASE_URL`
- **Google Drive:** `GOOGLE_APPLICATION_CREDENTIALS` (service account path, validated by `drive_client.py`)
- **Orchestrator runtime:** `SKIP_HUMAN_REVIEW`, `OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.digitalharmonyai.com`
- **Grafana:** `GRAFANA_ADMIN_PASSWORD` (⚠️ audit SEC-2 still hardcoded `admin123` in override)
- **Frontend:** `NEXT_PUBLIC_LANGGRAPH_URL`, `NEXT_PUBLIC_GRAFANA_URL` (recommended for MAJ-7 fix)

**Secret hygiene:** `.gitignore` has `.env`. `runtime.env` at `langgraph_workflows/dhg-agents-cloud/runtime.env` is tracked but contains only non-secret config per its own header (`SKIP_HUMAN_REVIEW=false`, OTel endpoint). Secrets backup at `/home/swebber64/DHG/aifactory3.5/secrets_backup_20260127.env` (outside repo).

---

## 11. Git Status

- **Branch:** `master` (current default)
- **Remote:** https://github.com/sdnydude/dhgaifactory3.5.git
- **Status:** 323 commits landed since March 3 audit
- **Recent commits:**
  ```
  5a915a4 feat(medkb): Plan 1 Phases 1-3 — dense retrieval, generation, hybrid + CRAG
  88d51a8 feat(medkb): shared test conftest, CLAUDE.md architecture updates
  c10424b fix(medkb): pass Ollama base_url to ChatOllama via llm_factory
  b01defc feat(medkb): Phase 3 — hybrid retrieval, CRAG graph, grade/rewrite nodes
  b12a50f feat(medkb): auth module, /v1/retrieve endpoint, readyz dependency checks
  2d3f609 Merge feature/phase3-foundation-llmanager: auth foundation + LLManager inbox
  2464202 feat(security): add RBAC, Cloudflare JWT auth, audit logging, and admin endpoints
  28553ca decommission: remove LibreChat, Docker disk cleanup
  dbafae9 decommission: remove Dify, RAGFlow, and legacy agents
  3140b87 feat(infra): healthchecks, OTel tracing, doc consolidation, API tests
  ```
- **Active worktrees:** 9 Claude Code worktrees under `.claude/worktrees/` (sleepy-joliot-b83e14 is the current audit worktree)
- **Open branches:** dependabot PRs for `next 16.1.6→16.2.3`, `cryptography`, `python-multipart`

### Commit-style rules
- **Never fast-forward merge** — always `git merge --no-ff` (merge commits allow single-revert rollback; see `MEMORY.md` feedback_no_fast_forward)
- **No co-author trailers** (see `MEMORY.md` feedback_no_coauthor)

---

## 12. DHG Style Guide

| Element | Light | Dark |
|---------|-------|------|
| Background | #FAF9F7 (warm off-white, NOT pure white) | #1A1D24 |
| Surface | #FFFFFF | #27272A |
| Surface Elevated | #FFFFFF | #32374A |
| Text Primary | #32374A (Graphite) | #FAF9F7 |
| Text Secondary | #71717A | #A1A1AA |
| Accent/Focus | #663399 (Purple) | #A78BFA |
| Border | #E4E4E7 | #3F3F46 |

**Brand tokens:** Graphite `#32374A` · Purple `#663399` · Orange `#F77E2D`
**Font:** Inter
**Layout rule:** 60-30-10
**Tagline:** "AI Agents In Tune With You"

**Rule:** Use semantic CSS tokens (`--dhg-background`, `--dhg-text-primary`, `--dhg-border-focus`), not raw hex values. All UIs must support both light and dark modes.

---

## 13. Prioritized Action Items (from `docs/AUDIT_REPORT_2026-04-19.md`)

| # | Priority | What | Effort | Source |
|---|----------|------|--------|--------|
| 1 | 🔴 P0 | Rotate `POSTGRES_PASSWORD` + `GRAFANA_ADMIN_PASSWORD`; remove from git (`weenie64`, `admin123`) | 1 hr | CRIT-2, SEC-2 |
| 2 | 🔴 P0 | Add `Depends(get_current_user)` + RBAC checks to all business endpoints | 4 hr | CRIT-1 |
| 3 | 🔴 P0 | Flip `SKIP_HUMAN_REVIEW` default to `"false"`; verify LangSmith Secrets UI override | 30 min | CRIT-3 |
| 4 | 🔴 P0 | Fix `intake_prefill_agent.py` TypedDict import | 5 min | CRIT-4 |
| 5 | 🔴 P0 | Disable or repair `dhg-medkb-ingestor` healthcheck | 15 min | MAJ-1 |
| 6 | 🔴 P0 | Implement real shared-secret auth in `medkb/auth.py` | 1 hr | MAJ-2 |
| 7 | 🟡 P1 | Replace 8 bare `except:` in grant_writer + compliance_review | 30 min | MAJ-3 |
| 8 | 🟡 P1 | Introduce `llm_factory.py`; replace 11 hardcoded `ChatAnthropic(...)` calls | 6 hr | MAJ-4 |
| 9 | 🟡 P1 | pdf-renderer worker: add `SKIP LOCKED` + retry columns (migration 011) | 2 hr | MAJ-5 |
| 10 | 🟡 P1 | Delete `registry/websocket_manager.py` dead-code stub | 5 min | MAJ-6 |
| 11 | 🟡 P1 | `/dashboards/page.tsx`: replace hardcoded `10.0.0.251` with env vars / Cloudflare subdomains | 1 hr | MAJ-7 |
| 12 | 🟡 P1 | Rename `NEXT_PUBLIC_SECURITY_DEV_MODE` to server-only `SECURITY_DEV_MODE`; add CI assertion | 1 hr | MAJ-8 |
| 13 | 🟡 P1 | pdf-renderer: stop importing `registry/models.py` — mirror schema locally | 3 hr | MAJ-9 |
| 14 | 🟡 P1 | `session-logger`: use `dhg-ollama:11434` DNS instead of `172.17.0.1` | 5 min | MAJ-10 |
| 15 | 🟡 P1 | Fix `.env.example` AI_FACTORY_REGISTRY_URL | 5 min | MAJ-11 |
| 16 | 🟡 P1 | `docker rm dhg-cme-research-agent`; archive local LangGraph compose | 5 min | MAJ-12 |
| 17 | 🟡 P1 | Add smoke test for each untested agent (8 files) | 2 hr | MAJ-13 |
| 18 | 🟡 P1 | Enumerate CORS `allow_headers`; remove `*` | 15 min | MAJ-14 |
| 19 | 🟡 P1 | Add CSP, X-Frame-Options, HSTS, Referrer-Policy to `next.config.ts` | 30 min | SEC-4 |
| 20 | 🟡 P1 | `npm audit fix`; verify CopilotKit AG-UI bridge | 1 hr | SEC-5 |
| 21 | 🟡 P1 | Add `v` field + rotation support to `EXPORT_SIGNING_SECRET` | 2 hr | SEC-6 |
| 22 | 🟡 P1 | Shared-secret header on `/webhooks/alertmanager` | 30 min | SEC-7 |
| 23 | 🟡 P2 | Kill the March backlog tail (legacy compose blocks, Archive/, .DS_Store, findings.md) | 1 hr | MIN-1,2,3,11 |
| 24 | 🟡 P2 | Pin `ollama/ollama` to a specific tag | 5 min | MIN-4 |
| 25 | 🟡 P2 | Move `dhg-logo-maker` onto `dhg-network`; delete stale empty networks | 15 min | MIN-5,6 |
| 26 | 🟡 P2 | Add healthcheck + `DRY_RUN=true` default to `dhg-remediator` | 30 min | MIN-7 |
| 27 | 🟡 P2 | Medkb Phase 4 (ingestor pipeline) + Phase 5 (production hardening) | TBD | project_medkb_rag_service.md |

**Total estimated effort:** ~28 hours for Critical + Major block, ~4 hours for Minor.

---

## 14. Claude Code Prompt

```
You are working on the DHG AI Factory project at /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/
on a Linux server (Ubuntu 24.04, Docker 29.1.5, RTX 5080 GPU, 64GB RAM).

## Quick Context
- Multi-agent CME (Continuing Medical Education) content generation platform
- Gen 2 LangGraph system is PRODUCTION. 17 graphs (13 agents + 3 composition + intake_prefill)
  registered in langgraph.json. Runs on LangGraph CLOUD, not locally:
    URL: https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app
    Auth: x-api-key header with LANGCHAIN_API_KEY
  Local port 2026 is DEV ONLY.
- Gen 3 frontend is PRODUCTION: Next.js 16 + shadcn/ui + assistant-ui + CopilotKit on port 3000
  (dhg-frontend). Connects to LangGraph Cloud via langgraph-sdk and to Registry API via
  server-side proxy that forwards the Cloudflare Access JWT.
- Legacy web-ui/ DECOMMISSIONED. Legacy agents/ DECOMMISSIONED (restart:"no").
- Dify, RAGFlow, LibreChat all DECOMMISSIONED April 2026.
- Registry API: FastAPI on port 8011, PostgreSQL 15 + pgvector, 64 tables, 227 tests.
- medkb RAG-as-a-Service: ports 5435 (db), 6381 (cache), 8015 (api). Plan 1 Phases 0-3 done.
- pdf-renderer: sibling service, internal-only, md-only project bundler + Google Drive sync.
- Auth: 4-layer defense — Cloudflare Access → Next.js middleware → FastAPI (JWT) → PG RBAC.
  5 roles seeded: admin, operations, finance, editor, viewer.
  (⚠️ audit CRIT-1: FastAPI JWT dependency only applied to /api/v1/security/* endpoints.)
- Observability: Prometheus (:9090), Grafana (:3001), Loki (:3100), Tempo (:3200),
  Alertmanager (:9093), Promtail, cAdvisor, Node Exporter, Postgres Exporter — all healthy.
- LangGraph dual tracing: @traceable (LangSmith) + @traced_node (OTel) on every node.
- Cloudflare Tunnel: app.digitalharmonyai.com → :3000, vs.digitalharmonyai.com → :8013.
- Git: on master branch. 323 commits since March 3. 9 Claude Code worktrees under .claude/.

## Critical Architecture Rules
1. LangGraph is the SOLE orchestration platform. Production runs in LangGraph Cloud.
2. Legacy agents/ is DECOMMISSIONED — do not build on it. Code kept for reference only.
3. Docker network for main stack: dhgaifactory35_dhg-network (compose project directory name).
4. Container names must use dhg- prefix.
5. AI_FACTORY_REGISTRY_URL = http://dhg-registry-api:8000 (NEVER 8500 — see audit MAJ-11).
6. Never fast-forward merge — always git merge --no-ff.
7. No co-author trailers on commits.
8. STOP and ask before touching production — never modify running services or rebuild
   containers without explicit Stephen approval.

## Key Files to Read First
- CLAUDE.md — canonical project truth
- docs/AUDIT_REPORT_2026-04-19.md — fresh audit with CRIT/MAJ/SEC findings
- docs/TODO.md, docs/BURNDOWN.md — current priorities
- docker-compose.yml + docker-compose.override.yml — main + observability stack
- langgraph_workflows/dhg-agents-cloud/langgraph.json — 17 graph definitions
- langgraph_workflows/dhg-agents-cloud/src/orchestrator.py — 3 composition graphs
- registry/api.py, registry/auth.py, registry/export_endpoints.py
- services/medkb/src/medkb/, services/pdf-renderer/
- frontend/src/middleware.ts, frontend/src/app/api/registry/[...path]/route.ts

## Rules for Collaboration
1. Production code only — no stubs, no placeholders, no TODOs.
2. One fix per hypothesis when debugging. If it fails, form a new hypothesis.
3. View files before editing. State what you're changing and why.
4. Run verification after any change. Show proof it works.
5. Never expose secrets — show first 10 chars max + *** when absolutely necessary.
6. DHG Style Guide: warm off-white #FAF9F7, purple #663399, Inter font, 60-30-10 layout,
   dark mode mandatory.
7. Use the LSP tool for workspace symbols (goToDefinition/findReferences/hover). For
   library symbols, use `hover` — pyright does not navigate into 3rd-party packages by
   design; a successful hover is proof the symbol is resolved.
8. CodeGraph is available: .codegraph/ exists. Use codegraph_search / codegraph_callers /
   codegraph_impact in main session. Spawn Explore subagent for open-ended "how does X
   work?" questions (do NOT call codegraph_explore directly in main session).

## Current Top Priorities (from audit 2026-04-19)
1. Rotate weenie64 + admin123 passwords (in git, repo is public)
2. Add Depends(get_current_user) to all business endpoints (auth exists, not applied)
3. Flip SKIP_HUMAN_REVIEW default to "false"; verify LangSmith Secrets UI
4. Fix intake_prefill_agent.py TypedDict import
5. Fix medkb auth (currently echoes any header)
```

---

## 15. Auth & RBAC (NEW section — April 2026)

4-layer defense-in-depth:

1. **Cloudflare Access WAF** — Google OAuth, httpOnly `CF_Authorization` cookie + `Cf-Access-Jwt-Assertion` header, account `Swebber@fafstudios.com`.
2. **Next.js middleware** (`frontend/src/middleware.ts`, Edge Runtime) — JWT cookie check, route guard, role-based visibility.
3. **FastAPI middleware** (`registry/auth.py`) — JWT signature validation against JWKS, `get_current_user`, `require_permission`, `require_role` dependencies. ⚠️ **audit CRIT-1:** only applied to `/api/v1/security/*`.
4. **PostgreSQL RBAC tables** (migration 004) — `security_users`, `security_roles`, `security_user_roles`, `security_project_access`, `security_audit_log`.

**Dev mode:** `SECURITY_DEV_MODE=true` bypasses all backend auth. `NEXT_PUBLIC_SECURITY_DEV_MODE=true` bypasses frontend auth and seeds a `DEV_USER` admin in Zustand. ⚠️ audit MAJ-8: rename to server-only.

**Frontend session flow:** `app/api/auth/me/route.ts` + `useSession` hook + Zustand `session-store` (memory-only, no localStorage). Session auto-initializes on app mount.

---

## 16. LLManager Review Inbox (NEW section — April 2026)

Human-in-the-loop workflow for LangGraph interrupted threads at `/inbox`.

**Layout:** Master-detail. Left sidebar lists pending interrupted threads from LangGraph SDK. Right panel shows document, AI quality assessment, decision bar.

**Components** (`frontend/src/components/review/`): inbox-master-detail, review-panel, reflection-panel, metrics-bar, decision-bar, document-viewer, vs-alternatives.

**Store:** Zustand `review-store.ts`.

**API:** `frontend/src/lib/inboxApi.ts` — queries LangGraph SDK for interrupted threads, resumes with decisions (approve / revise / reject).

**AI Reflection:** Quality signals (prose score, banned patterns, ACCME compliance) + approve/revise recommendation. Auto-refreshes every 30s.

**Empty state:** Shows demo data with banner and action guard (`504b25e`, `58e5cfc`).

---

## 17. Inbox Document & Project Download (NEW section — tagged `phase2v2`, merged Apr 16)

Two-layer export feature — Phase 1 single-document sync, Phase 2 v2 async multi-document bundles + Google Drive sync.

**Phase 1 — Single-document sync (DONE):**
- `dhg-pdf-renderer` sibling service — Playwright renders, waits for `[data-print-ready=true]`, calls `page.pdf()`
- HMAC-signed print tokens (`registry/export_signing.py` mint + `frontend/src/lib/printTokens.ts` Edge-Runtime verifier)
- `/print/cme/document` Next.js print route with middleware bypass gated by HMAC token
- `/api/cme/export/document` registry endpoint — mints token, calls pdf-renderer `/render-sync`, streams PDF back
- Playwright E2E at `frontend/e2e/inbox-document-download.spec.ts`

**Phase 2 v2 — Async bundles + Drive sync (DONE Apr 16, tagged `phase2v2`):**
- `download_jobs` v2 schema (migrations 009 + 010) with `scope ∈ {document, project_bundle, drive_sync}` CHECK constraint
- Endpoints under `/api/cme/export/`: `projects`, `projects/{id}/documents`, `bundle` (enqueue), `job/{id}`, `jobs`, `artifact/{id}`
- md-only project bundler (`services/pdf-renderer/bundler.py`) — atomic zip writer, `manifest.json`, deferred PDF-in-bundle to Phase 3
- Google Drive service-account client (`drive_client.py`) + drive sync action (`drive_sync.py`) with `manifest.json` reconciliation
- Worker loop (`worker.py`) — `FOR UPDATE` row claim (⚠️ audit MAJ-5: should be `SKIP LOCKED`), three-scope dispatch
- Orchestrator hook: `src/drive_sync.py` exposes `enqueue_drive_sync` helper; recipe milestones wire project state → Drive
- Frontend: Files tab Zustand store (expanded, selected, preview), downloads tray, `use-download-polling` hook
- 5-test E2E suite (`inbox-project-bundle.spec.ts`)
- **Critical fix preserved:** `frontend/src/app/api/registry/[...path]/route.ts:43` uses `arrayBuffer()` (commit `b736357`) to keep PDF/zip bodies binary-safe through the proxy

---

## 18. medkb RAG-as-a-Service (NEW section — April 2026)

Central Retrieval-Augmented Generation service for medical knowledge, designed to be LLM-agnostic.

**Stack:**
- `dhg-medkb-db` (pgvector/pgvector:pg15, port 5435)
- `dhg-medkb-cache` (Redis 7, port 6381, 4GB LRU)
- `dhg-medkb-api` (FastAPI, port 8015)
- `dhg-medkb-ingestor` (Phase 5 stub — currently unhealthy, see audit MAJ-1)

**Graph design** (`services/medkb/src/medkb/graph/`): redact → analyze_query → retrieve_fan → rerank → format_cite → generate → grade → (rewrite if fail) → emit_feedback. CRAG (Corrective RAG) pattern with hybrid dense/BM25 retrieval.

**Current state:** Plan 1 Phases 0–3 complete (51 commits, 46 tests, 4 containers running). Next: Phase 4 (ingestor pipeline) + Phase 5 (production hardening).

**Key endpoints:**
- `POST /v1/query` — full RAG pipeline with generation
- `POST /v1/retrieve` — retrieval only, no generation
- `GET/POST /v1/corpora` — corpus CRUD
- `GET /v1/healthz`, `/v1/readyz`

**Design spec:** `docs/superpowers/specs/2026-04-17-medkb-rag-as-a-service-design.md`
**Plan 1:** `docs/superpowers/plans/2026-04-17-medkb-plan1-foundation.md`

**Known risks:** audit MAJ-2 (`auth.py:resolve_caller` echoes any header — fully open), MAJ-1 (ingestor healthcheck broken).

---

## 19. Cloudflare Tunnel (NEW section)

Stephen's networking + edge configuration. All public access to DHG services transits Cloudflare; there is no direct inbound from the internet to `10.0.0.251`.

**Tunnel:** ID `30437aa6-d3f8-4c52-85cc-be0a0bfe8478`, running as a systemd service (`cloudflared`), config at `/etc/cloudflared/config.yml`.

**Routes:**
| Subdomain | Target | Purpose |
|-----------|--------|---------|
| `app.digitalharmonyai.com` | `localhost:3000` | Next.js frontend |
| `vs.digitalharmonyai.com` | `localhost:8013` | VS Engine |
| `otel.digitalharmonyai.com` | Tempo OTLP/HTTP | Receives OTel spans from LangGraph Cloud |
| `c2l.digitalharmonyai.com` | REMOVED | Was pointing to port 5000 (nothing listening) |
| `secrets.digitalharmonyai.com` | REMOVED | Was Infisical |

**Edge protections:** Cloudflare handles SSL termination; Cloudflare Access + Google OAuth gates all routes. Any local service can be internet-exposed by adding one line to `config.yml` + `systemctl restart cloudflared`.

**Recommended additions** (audit MAJ-7): `grafana.digitalharmonyai.com`, `prom.digitalharmonyai.com`, etc., for dashboard tile URLs instead of hardcoded LAN IPs.

---

## 20. Production Rules (lifted from CLAUDE.md for self-contained reference)

1. **Version control is the sole source of truth.** Sequential phases only. No overlapping or speculative work.
2. **No placeholders, TODOs, or provisional logic.** Every file must work on first deploy.
3. **One fix per hypothesis when debugging.** If it fails, form a new hypothesis.
4. **View files before editing.** State what you're changing and why.
5. **Run verification after any change.** Show proof it works.
6. **No silent refactors.** No behavior changes without operational rationale.
7. **Written change request required.** Map to phase + acceptance criteria.
8. **Make assumptions explicit.** Do not invent requirements.
9. **Definition of done:** Works in real conditions, no data loss on restart/refresh, state is unambiguous, commit history reflects intent.
10. **Overhead IS the quality.** Standards, processes, rigor, and thorough planning are the product clients pay for. Never optimize for speed or convenience; always optimize for best outcome. Fortune 500 execution.
11. **Planning and building are separate phases.** Do not write files, run commands, or generate code until the design/plan is fully worked through AND Stephen explicitly approves moving to implementation.

**Debug Protocol:** PAUSE → RESEARCH → HYPOTHESIZE (2-3 ranked) → PLAN → FIX (1 per hypothesis) → VERIFY → DOCUMENT. If 3 hypotheses fail, escalate.

**Honesty Protocol:** Never claim confidence without verification. Distinguish assumptions from facts. Truth over helpfulness.

**Secret Safety:** Never `cat .env` or echo secrets. Show first 10 chars + `***` max. On accidental exposure: STOP, inform, recommend rotation.

---

## 21. What's Intentionally Omitted

- Full contents of all 64 database table schemas (available via `\d+ table_name` in psql)
- Full contents of all 13 agent source files (paths listed in §5)
- Full contents of all archived docs (`docs/archive/`, 55+ files)
- Specific API key values (see `.env` on server; never in repo)
- Infisical stack details at `/home/swebber64/infisical-stack/` (separate stack, independent)
- Transcribe Pipeline internals (separate stack on `dhg-transcribe_default` network)
- Full PostHog integration (see `MEMORY.md` → `project_posthog.md`)
- Full CodeGraph operator notes (see `~/.claude/CLAUDE.md` and `.claude/rules/codegraph.md`)
- LSP tool usage details (see `docs/superpowers/specs/2026-04-14-lsp-setup-design.md`)
