# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DHG AI Factory is a production-grade multi-agent orchestration system for CME (Continuing Medical Education) and non-CME content generation. It uses 7+ specialized FastAPI agents running in Docker, with PostgreSQL/pgvector for state persistence and LibreChat as the user interface.

## Architecture

```
User → LibreChat (3010) → DHG Agents (8002-8012) → PostgreSQL (5432)
                                    ↓
                            Ollama (11434) for local LLM
```

### Agent Ports
| Port | Agent | Purpose |
|------|-------|---------|
| 8002 | Medical LLM | Clinical content generation (ICD-10, guidelines) |
| 8003 | Research | Evidence from 9+ sources (PubMed, CDC, CMS, etc.) |
| 8004 | Curriculum | Learning objectives, Moore Levels mapping |
| 8005 | Outcomes | Pre/post/6-week assessments |
| 8006 | Competitor Intel | Market intelligence |
| 8007 | QA/Compliance | ACCME validation, fair balance, hallucination checks |
| 8008 | Visuals/Media | Image generation |
| 8009 | Session Logger | Session tracking |
| 8012 | Logo Maker | Brand assets |

### Other Services
- **Registry DB** (5432): PostgreSQL with pgvector for embeddings
- **LibreChat** (3010): Chat interface
- **Ollama** (11434): Local LLM inference (qwen3:14b)
- **pgAdmin** (5050): Database management

## Build & Run Commands

### Full System
```bash
docker compose up -d           # Start all services
docker compose ps              # Check status
docker compose logs -f <svc>   # View logs
docker compose down            # Stop services
```

### Health Check
```bash
# All agent endpoints
for port in 8002 8003 8004 8005 8006 8007 8008; do
  curl -s http://localhost:$port/health
done
```

### Single Service Rebuild
```bash
docker compose build <service>           # Rebuild image
docker compose build --no-cache <service> # Force rebuild
docker compose up -d <service>           # Restart single service
```

## Database

```bash
# Connect to PostgreSQL
docker exec -it dhg-registry-db psql -U dhg -d dhg_registry

# Via pgAdmin
# http://localhost:5050
```

Key tables: `cme_projects`, `agents`, `references`, `events`, `antigravity_chats`

## Key Technologies

- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic 2.5
- **Database**: PostgreSQL 15 + pgvector
- **LLMs**: OpenAI/Anthropic APIs, Ollama for local inference
- **UI**: LibreChat

## Code Organization

```
agents/
  medical-llm/      # Clinical content generation
  research/         # Multi-source evidence gathering
  curriculum/       # Learning objective design
  outcomes/         # Moore Levels assessment
  competitor-intel/ # Market intelligence
  qa-compliance/    # ACCME validation
  visuals/          # Image generation
  session-logger/   # Session tracking
  logo-maker/       # Brand assets

registry/           # PostgreSQL schema and models
scripts/            # Utility scripts
docs/               # Documentation
.agent/             # Antigravity workflows and rules
```

## CME vs NON-CME Modes

- **CME mode**: Enforces ACCME rules, fair balance, validated references
- **NON-CME mode**: No compliance restrictions, allows commercial language

## Environment Configuration

Key variables in `.env`:
- `REGISTRY_DB_URL`: PostgreSQL connection string
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`: LLM providers
- `OLLAMA_BASE_URL`: Local LLM endpoint

## Current Work (Feb 2026)

- **CME Intake Form**: PostgreSQL integration complete, LibreChat sidebar pending
- **LibreChat Agent Features**: Artifacts and Tools enablement pending

See `docs/TODO.md` for current priorities and `docs/PROJECT_TRUTH.md` for system status.
