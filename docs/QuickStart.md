# Quick Start Guide

Get the DHG AI Factory up and running.

## Prerequisites

- **Docker Desktop** (running)
- **Git**
- Access to server 10.0.0.251 (g700data1)

## For New Developers

### 1. Clone the repository

```bash
git clone https://github.com/sdnydude/dhgaifactory3.5.git
cd dhgaifactory3.5
git checkout feature/langgraph-migration
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys (OPENAI, ANTHROPIC, etc.)
```

### 3. Start the System

```bash
docker compose up -d
```

### 4. Verify Health

```bash
# Check container status
docker compose ps

# Check agent health endpoints
for port in 8002 8003 8004 8005 8006 8007 8008; do
  echo "Port $port: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:$port/health)"
done
```

## Accessing Interfaces

| Service | URL | Notes |
|---------|-----|-------|
| **LibreChat** | http://localhost:3010 | Main chat UI |
| **pgAdmin** | http://localhost:5050 | Database management |
| **Agent API Docs** | http://localhost:{port}/docs | Swagger docs per agent |

## Agent Ports

| Agent | Port |
|-------|------|
| Medical LLM | 8002 |
| Research | 8003 |
| Curriculum | 8004 |
| Outcomes | 8005 |
| Competitor Intel | 8006 |
| QA/Compliance | 8007 |
| Visuals/Media | 8008 |

## Troubleshooting

- **Services failing?** Check logs: `docker compose logs <service-name>`
- **Port conflicts?** Check: `lsof -i :<port>`
- **Database issues?** Connect via pgAdmin at :5050

## For VS Code Users (Remote-SSH)

1. Install "Remote - SSH" extension
2. Connect to `swebber64@10.0.0.251`
3. Open folder: `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5`

See `docs/TEAMMATE_SETUP.md` for detailed Antigravity setup.
