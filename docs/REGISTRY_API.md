# DHG Registry API Documentation

**Version:** 1.0  
**Base URL:** `http://10.0.0.251:8011`  
**Container:** `dhg-registry-api`  
**Port:** 8011 → 8000 (internal)

---

## Overview

The Registry API is the central data management service for the DHG AI Factory. It provides:

- **Agent Registry** — Register, discover, and manage AI agents
- **Antigravity Session Tracking** — Track coding assistant sessions and files
- **Research Request Management** — Store and retrieve research requests
- **Media & Transcription** — Manage media files, transcripts, and segments
- **Project & Conversation Storage** — Store Claude conversations and artifacts

---

## Quick Start

```bash
# Health check
curl http://10.0.0.251:8011/healthz

# List all antigravity sessions
curl http://10.0.0.251:8011/api/v1/antigravity/chats

# List registered agents
curl http://10.0.0.251:8011/api/v1/agents
```

---

## Authentication

Currently no authentication required (internal network only).

---

## Endpoints

### Health & Metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Health check endpoint |
| GET | `/metrics` | Prometheus metrics (write/read latency, operation counts, errors) |

### Agent Registry

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/agents/register` | Register a new agent |
| POST | `/api/v1/agents/{service_id}/heartbeat` | Agent heartbeat |
| GET | `/api/v1/agents` | List all agents |
| GET | `/api/v1/agents/{service_id}` | Get specific agent |
| GET | `/api/v1/agents/models/list` | List all available models |
| GET | `/api/v1/agents/discover` | Discover active agents |

### Antigravity Session Tracking

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/antigravity/chats` | List all Antigravity sessions |
| POST | `/api/v1/antigravity/chats` | Create/update a session |
| GET | `/api/v1/antigravity/chats/{conversation_id}` | Get specific session |
| PATCH | `/api/v1/antigravity/chats/{conversation_id}` | Update session metadata |
| GET | `/api/v1/antigravity/files` | List tracked files |
| POST | `/api/v1/antigravity/files` | Register a file |
| GET | `/api/v1/antigravity/files/{file_id}` | Get specific file |
| GET | `/api/v1/antigravity/chats/{conversation_id}/files` | Get files for session |

### Research Requests

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/research/requests` | List research requests |
| POST | `/api/v1/research/requests` | Create research request |
| GET | `/api/v1/research/requests/{request_id}` | Get specific request |

### Media & Transcription

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/media` | List media files |
| POST | `/api/v1/media` | Create media entry |
| GET | `/api/v1/media/{media_id}` | Get media file |
| GET | `/api/v1/transcripts` | List transcripts |
| POST | `/api/v1/transcripts` | Create transcript |
| GET | `/api/v1/transcripts/media/{media_id}` | Get transcripts for media |
| GET | `/api/v1/segments` | List segments |
| POST | `/api/v1/segments` | Create segment |
| GET | `/api/v1/segments/transcript/{transcript_id}` | Get segments for transcript |

### Events

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/events` | List events |
| POST | `/api/v1/events` | Create event |

### Projects & Conversations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects` | List projects |
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects/{project_id}` | Get project |
| GET | `/api/v1/conversations` | List conversations |
| POST | `/api/v1/conversations` | Create conversation |
| GET | `/api/v1/conversations/{conversation_id}` | Get conversation |
| GET | `/api/v1/conversations/search` | Search conversations |
| GET | `/api/v1/messages/conversation/{conversation_id}` | Get messages |

### Artifacts

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/artifacts` | List artifacts |
| POST | `/api/v1/artifacts` | Create artifact |
| GET | `/api/v1/artifacts/conversation/{conversation_id}` | Get artifacts for conversation |
| GET | `/api/v1/artifacts/{artifact_id}` | Get specific artifact |

### WebSocket

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/ws/status` | WebSocket status |

---

## Data Models

### Antigravity Chat

```json
{
  "id": "58d0aff9-c6d6-402d-bbef-2a25b1674948",
  "conversation_id": "f664d0d5-8e0b-45b9-8cbe-5af9d7a2c307",
  "title": "Fix .dockerignore Syntax Error",
  "summary": "Debugging Docker build issues...",
  "user_objective": "Build and deploy the app",
  "created_at": "2026-01-26T21:09:30.725716Z",
  "last_modified": "2026-01-26T21:09:30.725716Z",
  "message_count": 27,
  "total_tokens": 0,
  "total_cost_usd": 0.0,
  "status": "imported",
  "tags": ["docker", "debugging"],
  "file_count": 0
}
```

### Antigravity File

```json
{
  "id": "uuid",
  "conversation_id": "conversation-uuid",
  "file_path": "/path/to/file.py",
  "file_type": "py",
  "file_size_bytes": 1234,
  "artifact_type": "code",
  "summary": "Implementation of X",
  "created_at": "2026-01-27T00:00:00Z"
}
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `registry_write_latency` | Histogram | Database write latency (ms) |
| `registry_read_latency` | Histogram | Database read latency (ms) |
| `registry_write_operations` | Counter | Write operations by type |
| `registry_read_operations` | Counter | Read operations by type |
| `registry_errors` | Counter | Errors by type |
| `registry_db_errors` | Counter | Database connection errors |
| `registry_db_connections` | Gauge | Active DB connections |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `dhg-registry-db` | Database hostname |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_USER` | `dhg` | Database user |
| `POSTGRES_PASSWORD` | `changeme` | Database password |
| `POSTGRES_DB` | `dhg_registry` | Database name |

---

## Docker Deployment

```bash
# Build
docker build -t dhg-registry-api:latest ./registry

# Run
docker run -d \
  --name dhg-registry-api \
  --network dhgaifactory35_dhg-network \
  -p 8011:8000 \
  -e POSTGRES_HOST=dhg-registry-db \
  -e POSTGRES_USER=dhg \
  -e POSTGRES_PASSWORD=<password> \
  -e POSTGRES_DB=dhg_registry \
  dhg-registry-api:latest
```

---

## Database Schema

The registry uses PostgreSQL with pgvector extension. Tables:

- `media` — Media files
- `transcripts` — Transcriptions  
- `segments` — Transcript segments
- `events` — System events
- `projects` — Claude projects
- `conversations` — Claude conversations
- `messages` — Conversation messages
- `artifacts` — Code artifacts
- `antigravity_chats` — Antigravity sessions
- `antigravity_files` — Tracked files
- `agents` — Registered agents
- `research_requests` — Research requests

---

## API Documentation (Interactive)

OpenAPI/Swagger docs available at:
- **Swagger UI:** http://10.0.0.251:8011/docs
- **ReDoc:** http://10.0.0.251:8011/redoc
- **OpenAPI JSON:** http://10.0.0.251:8011/openapi.json
