# DHG AI Factory - CME Content Generation Platform

## Overview
AI Factory platform for ACCME-compliant CME content generation. Uses Onyx/Danswer for RAG, multi-LLM selector (Local LLM → Gemini → Claude), and integrated transcription services.

## Architecture

### Replit (This App)
- **Frontend**: React + Vite (port 5000)
- **Gateway**: FastAPI orchestrator (port 8000)
- Connects to your locally-hosted backend services

### Local Infrastructure (Your Machine)
Run `infrastructure/setup.sh` to start:
- **Onyx/Danswer**: RAG platform with Vespa search (ports 3000, 8080)
- **PostgreSQL**: Central database (port 5432)
- **Ollama**: Local LLM (port 11434)
- **Whisper**: Transcription (port 9090)

## Key Files

### Infrastructure (`infrastructure/`)
| File | Purpose |
|------|---------|
| `setup.sh` | Install and start all services |
| `docker-compose.yml` | Service definitions |
| `verify.sh` | Health checks |
| `backup.sh` / `restore.sh` | Data management |

### Frontend (`web-ui/`)
- React 19 + Vite + Tailwind CSS
- Design Generator (Gemini image generation)
- Audio Studio (WebAudio processing)
- Transcription Harmony (coming)

### Backend (`agents/orchestrator/`)
- FastAPI gateway
- LLM selector service
- WebSocket connections

## Workflows
1. **Web UI** - React frontend on port 5000
2. **Backend API** - FastAPI on port 8000

## Setup Instructions

### 1. Local Infrastructure
```bash
cd infrastructure
chmod +x *.sh
./setup.sh
```

### 2. Configure Replit
Set environment variables:
```
ONYX_API_URL=http://YOUR_IP:8080
OLLAMA_URL=http://YOUR_IP:11434
WHISPER_URL=http://YOUR_IP:9090
```

## Recent Changes (December 2025)
- Added infrastructure setup scripts for local deployment
- Configured Onyx/Danswer with Vespa, PostgreSQL, Redis
- Added Ollama for local LLM
- Added Whisper for transcription
- Full docker-compose with health checks

## Planned
- Transcription Harmony page
- Multi-LLM selector implementation
- AudioStudio UI fixes
- Connect frontend to Onyx RAG
