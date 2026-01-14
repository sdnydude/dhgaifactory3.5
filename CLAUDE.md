# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DHG AI Factory is a production-grade multi-agent orchestration system for CME (Continuing Medical Education) and non-CME content generation. It uses 7 specialized FastAPI agents coordinated by a master orchestrator, with PostgreSQL/pgvector for state persistence and a React frontend.

## Architecture

```
User Request → Orchestrator (8011)
    ├─ Detects: CME vs NON-CME mode automatically
    ├─ Routes to specialized agents (8002-8007)
    ├─ Coordinates parallel + sequential task execution
    └─ QA/Compliance validates ACCME rules (CME mode only)
         ├─ If violations → Medical LLM corrects
         └─ Final deliverables returned with audit trail
```

### Agent Ports
| Port | Agent | Purpose |
|------|-------|---------|
| 8011 | Orchestrator | Master coordinator, LangGraph state management |
| 8002 | Medical LLM | Clinical content generation (ICD-10, guidelines) |
| 8003 | Research | Evidence from 9+ sources (PubMed, CDC, CMS, etc.) |
| 8004 | Curriculum | Learning objectives, Moore Levels mapping |
| 8005 | Outcomes | Pre/post/6-week assessments |
| 8006 | Competitor Intel | Market intelligence |
| 8007 | QA/Compliance | ACCME validation, fair balance, hallucination checks |

### Other Services
- **Registry DB** (5432): PostgreSQL with pgvector for embeddings
- **Web UI** (3005 prod, 5173 dev): React/Vite frontend
- **Ollama** (11434): Local LLM inference
- **Prometheus** (9090) / **Grafana** (3000): Observability

## Build & Run Commands

### Full System
```bash
make setup          # First time: create secrets and directories
cp .env.example .env && vim .env  # Configure API keys
make up             # Start all services (Docker Compose)
make health         # Verify all services healthy
make down           # Stop services
make restart        # Full restart (down + up)
make logs           # Tail all service logs
make status         # Show Docker Compose status
```

### Single Service Rebuild
```bash
docker-compose build orchestrator           # Rebuild image
docker-compose build --no-cache orchestrator # Force rebuild
docker-compose up -d orchestrator           # Restart single service
docker-compose logs -f orchestrator         # View logs
```

### Web UI Development
```bash
cd web-ui
npm install         # Install dependencies
npm run dev         # Vite dev server (port 5173)
npm run build       # Production build
npm run lint        # ESLint check
```

## Testing

### Integration Tests
```bash
# Full CME pipeline
curl -X POST http://localhost:8011/orchestrate \
  -H "Content-Type: application/json" \
  -d @test_requests/needs_assessment_diabetes.json

# NON-CME workflow
curl -X POST http://localhost:8011/orchestrate \
  -H "Content-Type: application/json" \
  -d @test_requests/business_strategy_digital_cme.json

# Health check
curl http://localhost:8011/health
```

### Interactive API Docs
All agents expose Swagger docs at `http://localhost:{port}/docs`

## Database

```bash
# Connect to PostgreSQL
docker-compose exec registry-db psql -U dhg -d dhg_registry

# Backup/restore
make backup
make restore BACKUP=dhg_registry_YYYY-MM-DD_HH-MM-SS.sql.gz
```

Key tables: `references`, `events`, `api_cache`, `segments`, `assessments`, `outcomes`

Schema defined in `registry/init.sql`

## Key Technologies

- **Backend**: FastAPI, LangGraph (workflow orchestration with PostgreSQL checkpointing), SQLAlchemy 2.0, Pydantic 2.5
- **Frontend**: React 19, Vite 7, Framer Motion, react-resizable-panels
- **Database**: PostgreSQL 15 + pgvector
- **LLMs**: OpenAI/Anthropic APIs, Ollama for local inference
- **Observability**: Prometheus, Grafana, structlog (JSON logging)

## Code Organization

```
agents/
  orchestrator/     # Master coordination (LangGraph + FastAPI)
  medical-llm/      # Clinical content generation
  research/         # Multi-source evidence gathering
  curriculum/       # Learning objective design
  outcomes/         # Moore Levels assessment
  competitor-intel/ # Market intelligence
  qa-compliance/    # ACCME validation
  visuals/          # Image generation (Google Gemini)
  shared/           # Common utilities (metrics, logging)

web-ui/             # React frontend
registry/           # PostgreSQL schema (init.sql)
scripts/            # healthcheck.sh, backup.sh, restore.sh
test_requests/      # Example JSON payloads for testing
```

## CME vs NON-CME Modes

The orchestrator automatically detects compliance mode based on task type:
- **CME mode**: Enforces ACCME rules, fair balance, no commercial bias, validated references (6-12 AMA-style), word count constraints (1000-1500 ±8%)
- **NON-CME mode**: No compliance restrictions, allows commercial language, competitive analysis

## Environment Configuration

Key variables in `.env` (see `.env.example`):
- `REGISTRY_DB_URL`: PostgreSQL connection string
- `CME_MODE_DEFAULT`: auto | cme | non-cme
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`: LLM providers
- `ACCME_STRICT_MODE`: Enable strict ACCME validation

## Scaling

```bash
docker-compose up -d --scale research=3 --scale medical-llm=2
```

## Troubleshooting

```bash
docker-compose logs {service}              # Check specific service logs
docker-compose build --no-cache {service}  # Force rebuild
docker-compose down -v && make up          # Reset database
```
