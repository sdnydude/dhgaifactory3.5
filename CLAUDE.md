# CLAUDE.md - Project Instructions for Claude Code

## Project Overview

**DHG AI Factory v3.5** - A production-ready, multi-agent system for generating ACCME-compliant CME content and NON-CME business materials. Features 16 specialized agents orchestrated through a master coordinator, backed by PostgreSQL with pgvector embeddings.

## Technology Stack

### Backend
- **Python 3.11** with FastAPI 0.104.1 + Uvicorn
- **LangGraph** for agent orchestration with PostgreSQL checkpoint persistence
- **PostgreSQL 15** + pgvector (1536-dimensional embeddings)
- **SQLAlchemy 2.0** + Alembic migrations
- **structlog** for JSON logging
- **Pydantic v2** for validation

### Frontend
- **React 19.2** with React Router v7
- **Vite 7.2** build tool
- **CSS** with CSS variables (Glassmorphism design)
- **Framer Motion** for animations

### Infrastructure
- **Docker** + Docker Compose orchestration
- **Nginx** reverse proxy
- **Prometheus** + Grafana monitoring
- **Ollama** for local LLM support

## Project Structure

```
dhgaifactory3.5/
├── agents/                    # 16 specialized agents
│   ├── orchestrator/          # Master coordinator (port 8011/8000)
│   ├── medical-llm/           # Medical NLP (port 8002)
│   ├── research/              # Evidence retrieval (port 8003)
│   ├── curriculum/            # Learning design (port 8004)
│   ├── outcomes/              # Assessment design (port 8005)
│   ├── competitor-intel/      # Market analysis (port 8006)
│   ├── qa-compliance/         # ACCME validation (port 8007)
│   ├── visuals/               # Image generation (port 8008)
│   └── shared/                # Shared utilities, metrics
├── web-ui/                    # React PWA frontend (port 3005)
├── registry/                  # Database schema & migrations
├── infrastructure/            # Production deployment stack
├── observability/             # Prometheus/Grafana/Loki configs
├── docker-compose.yml         # Main service orchestration
├── Makefile                   # Task automation
└── .env.example               # Configuration template
```

## Build & Run Commands

### Using Make (Recommended)
```bash
make setup          # Create secrets and directories
make up             # Start all services
make down           # Stop services
make restart        # Full restart
make logs           # Follow logs
make health         # Health check all services
make backup         # Create database backup
make restore BACKUP=filename
```

### Docker Compose
```bash
docker-compose build           # Build all images
docker-compose up -d           # Start in background
docker-compose logs -f         # Follow logs
docker-compose down            # Stop all services
```

### Web UI Development
```bash
cd web-ui
npm install                    # Install dependencies
npm run dev                    # Vite dev server (port 5173)
npm run build                  # Production build
npm run lint                   # ESLint check
```

### Agent Development
```bash
cd agents/<agent-name>
pip install -r ../shared/requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Coding Conventions

### Python Backend
- Use `async/await` patterns with FastAPI
- Use `structlog` for all logging (JSON format)
- Use Pydantic v2 models for request/response validation
- Add full type annotations (e.g., `async def process() -> Dict[str, Any]`)
- Use `HTTPException` for API errors
- Include `/health` endpoint on all agents
- Define system prompts as `SYSTEM_PROMPT` constant

### React Frontend
- Functional components with React hooks only
- Use Context API (StudioProvider pattern) for state
- Use CSS variables for theming (--color-*, --space-*, --glass-*)
- Use `useWebSocket` hook for real-time communication
- Handle errors with Error Boundaries

### Database
- Use `asyncpg` for async database operations
- Log all operations to `events` table
- Use pgvector for embeddings (1536 dimensions)

## Service Ports

| Service | External | Internal | Purpose |
|---------|----------|----------|---------|
| Orchestrator | 8011 | 8000 | Master coordination |
| Medical LLM | 8002 | 8002 | Medical NLP |
| Research | 8003 | 8003 | Evidence retrieval |
| Curriculum | 8004 | 8004 | Learning design |
| Outcomes | 8005 | 8005 | Assessment design |
| Competitor Intel | 8006 | 8006 | Market analysis |
| QA/Compliance | 8007 | 8007 | Validation |
| Visuals | 8008 | 8008 | Image generation |
| Web UI | 3005 | 5173 | Frontend |
| PostgreSQL | 5432 | 5432 | Database |
| Ollama | 11434 | 11434 | Local LLMs |

## Compliance Rules

### CME Mode (ACCME Enforcement)
- Fair balance required - no commercial bias
- Evidence-based content only
- No trade names without disclosure
- Learning objectives with Moore Levels 1-7 mapping
- Word count constraints (920-1620 for needs assessment)
- 6-12 AMA-style references required
- URL validation mandatory

### NON-CME Mode
- No ACCME restrictions
- Commercial language allowed
- Competitive analysis permitted

## Testing & Debugging

### Health Checks
```bash
make health
# Or manually:
curl http://localhost:8011/health
```

### Database Inspection
```bash
docker-compose exec registry-db psql -U dhg -d dhg_registry
SELECT * FROM events ORDER BY created_at DESC LIMIT 10;
```

### API Testing
```bash
curl -X POST http://localhost:8011/orchestrate \
  -H "Content-Type: application/json" \
  -d @test_requests/needs_assessment_diabetes.json
```

## Environment Variables

Critical variables (see `.env.example` for complete list):
- `POSTGRES_PASSWORD` - Database credentials
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - LLM providers
- `GOOGLE_AI_API_KEY` - Image generation (Visuals agent)
- `CME_MODE_DEFAULT` - auto/cme/non-cme
- `ACCME_STRICT_MODE` - Compliance enforcement (true/false)

## Key Files

- `docker-compose.yml` - Service orchestration
- `agents/orchestrator/main.py` - Master orchestrator logic
- `agents/orchestrator/langgraph_integration.py` - LangGraph workflow
- `registry/init.sql` - Database schema
- `web-ui/src/App.jsx` - Frontend routing
- `agents/shared/metrics.py` - Shared utilities

## Git Workflow

- Main branch: `master`
- Feature branches: `claude/<feature-name>-<session-id>`
- Always run `make health` before committing
- Run `npm run lint` for frontend changes
