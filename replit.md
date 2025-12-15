# DHG AI Factory - CME Pipeline Multi-Agent System

## Overview
The DHG AI Factory is a multi-agent system designed for automated generation of ACCME-compliant CME content and NON-CME business/strategy materials. It orchestrates specialized agents through a master orchestrator.

## Project Architecture

### Frontend (web-ui/)
- **Framework**: React 19 with Vite
- **Port**: 5000 (development)
- **Features**: Chat interface, sidebar navigation, admin panel, settings

### Backend (agents/orchestrator/)
- **Framework**: FastAPI with Python
- **Port**: 8000 (development, proxied via Vite)
- **WebSocket**: Connected via `/ws` endpoint
- **Dependencies**: fastapi, uvicorn, pydantic, structlog, httpx

### Agent Services (Docker-based, not running in Replit)
- Medical LLM Agent (port 8002)
- Research/Retriever Agent (port 8003)
- Curriculum Agent (port 8004)
- Outcomes Agent (port 8005)
- Competitor Intel Agent (port 8006)
- QA/Compliance Agent (port 8007)

## Workflows

### Development
1. **Web UI** - React frontend on port 5000
2. **Backend API** - FastAPI orchestrator on port 8000

### How the WebSocket Works
- Frontend connects to `/ws` which is proxied by Vite to the backend
- Backend handles chat messages and orchestration commands
- Supports streaming responses and status updates

## Recent Changes
- Configured for Replit environment (December 2025)
- Added Vite proxy for WebSocket connections
- Updated WebSocket URL to use dynamic host detection
- Installed compatible FastAPI/Starlette versions

## User Preferences
- None configured yet

## Known Limitations
- Individual agent services (medical-llm, research, etc.) require Docker and are not running in Replit
- The orchestrator provides demo responses when agents are unavailable
