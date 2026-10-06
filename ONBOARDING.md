# DHG AI Factory v3.5 — Onboarding Guide

## What Is This?

A multi-agent platform built on **LangGraph** that generates pharmaceutical-grade CME (Continuing Medical Education) grant documentation. Also a general-purpose modular enterprise AI system. CME is ~10% of DHG's revenue.

**Owner:** Stephen Webber — CEO/Founder, Digital Harmony Group. 35+ years in business development, medical education, and broadcast production. Expects Fortune 500 execution quality.

**Server:** g700data1 (10.0.0.251), Ubuntu 24.04, Docker 29.1.5, NVIDIA RTX 5080, 64GB RAM.

---

## Architecture at a Glance

### LangGraph Agents (CURRENT — Production)

17 graphs in `langgraph_workflows/dhg-agents-cloud/`. Production runs on **LangGraph Cloud**; local dev on port 2026.

- **13 content agents** — Needs Assessment, Research, Clinical Practice, Gap Analysis, Learning Objectives, Curriculum Design, Research Protocol, Marketing Plan, Grant Writer, Prose Quality, Compliance Review, Citation Checker, Registry
- **3 orchestrator recipes** — `needs_package`, `curriculum_package`, `grant_package` (parallel fan-out, quality gates, human review checkpoints)
- **Dual tracing** on every node: LangSmith (`@traceable`) + OpenTelemetry (`@traced_node`)

### Infrastructure Services

| Service | Port | Purpose |
|---------|------|---------|
| dhg-registry-db | 5432 | PostgreSQL 15 + pgvector (64 tables) |
| dhg-registry-api | 8011 | FastAPI data registry + Prometheus metrics |
| dhg-frontend | 3000 | Next.js (shadcn/ui + assistant-ui + CopilotKit) |
| dhg-ollama | 11434 | Local LLM (qwen3:14b, llama3.1:8b, nomic-embed-text) |
| dhg-medkb-api | 8015 | RAG-as-a-Service (dense + hybrid + CRAG retrieval) |
| dhg-pdf-renderer | internal | Playwright PDF + md-only project bundler + Drive sync |

### Observability

Prometheus (9090) + Grafana (3001) + Loki (3100) + Tempo (3200) + Alertmanager (9093) + cAdvisor + Node/Postgres exporters. 23 containers ingesting logs via Promtail.

### Auth

4-layer: Cloudflare Access WAF -> Next.js middleware -> FastAPI JWT validation -> PostgreSQL RBAC tables. Dev mode bypass via `SECURITY_DEV_MODE=true`.

---

## Key Paths

| What | Where |
|------|-------|
| LangGraph agents | `langgraph_workflows/dhg-agents-cloud/src/*.py` |
| Orchestrator | `langgraph_workflows/dhg-agents-cloud/src/orchestrator.py` |
| Registry API | `registry/api.py` |
| Registry services | `registry/*_service.py` (30 files) |
| Registry tests | `registry/test_*.py` (26 files, 514 tests) |
| Frontend | `frontend/src/` |
| medkb RAG service | `services/medkb/src/medkb/` |
| Observability | `observability/` |
| Docker compose | `docker-compose.yml` + `docker-compose.override.yml` |
| Current priorities | `docs/TODO.md` |
| Environment vars | `.env` (secrets -- never expose) |

---

## Build & Run

```bash
# Full system
docker compose up -d
docker compose ps

# LangGraph server (separate compose)
cd langgraph_workflows/dhg-agents-cloud && docker compose up -d

# Registry DB
docker exec -it dhg-registry-db psql -U dhg -d dhg_registry

# Health checks
curl -s http://localhost:8011/healthz       # Registry API
curl -s http://localhost:9090/-/healthy     # Prometheus

# Type-check quality gates
npx pyright                                 # Python
npm --prefix frontend run typecheck         # TypeScript
```

---

## Production Rules (Non-Negotiable)

1. **No placeholders, TODOs, or provisional logic** -- every file works on first deploy
2. **View files before editing** -- state what you're changing and why
3. **Run verification after any change** -- show proof it works
4. **One fix per hypothesis** when debugging
5. **Planning and building are separate phases** -- don't write code until design is approved
6. **Quality over speed** -- overhead IS the quality
7. **Never expose secrets** -- no `cat .env`, show first 10 chars max
8. **Always use `git merge --no-ff`** -- merge commits enable single-revert rollback
9. **Use 10.0.0.251 not localhost** for all URLs (except Docker-internal healthchecks)

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | LangGraph (StateGraph, Command pattern) |
| Agent LLM | Claude Sonnet via ChatAnthropic |
| Local LLM | Ollama (qwen3:14b, llama3.1:8b) |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic 2.5 |
| Database | PostgreSQL 15 + pgvector |
| Frontend | Next.js, shadcn/ui, assistant-ui, CopilotKit |
| Observability | Prometheus, Grafana, Loki, Tempo, LangSmith |
| Container runtime | Docker Engine 29.1.5 |

---

## Legacy Warning

`agents/` contains decommissioned Docker-based FastAPI agents (ports 8002-8008). All stopped with `restart: "no"`. **Do not build new features on these.** Current agents live in `langgraph_workflows/`.

---

## Memreg Pipeline

Automated capture system with 7 trigger types: corrections, bug_fixes, insights, decision_logs, deferred_items, test_coverage, ship_sessions. Rules in `.claude/rules/auto-*.md`, scripts in `~/.claude/scripts/post-*.sh`. 262+ events captured.

---

## DHG Brand

| Token | Value |
|-------|-------|
| Graphite | #32374A |
| Purple | #663399 |
| Orange | #F77E2D |
| Font | Inter |
| Background (light) | #FAF9F7 (warm off-white, NOT pure white) |

Use semantic CSS tokens, not raw hex values. Both light and dark modes required.
