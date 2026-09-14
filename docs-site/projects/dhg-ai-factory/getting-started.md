---
sidebar_position: 1
title: Getting Started
---

# DHG AI Factory v3.5

Multi-agent platform built on LangGraph that generates pharmaceutical-grade CME (Continuing Medical Education) grant documentation. Also serves as a general-purpose modular enterprise AI system.

## Quick Start

```bash
# Full system
docker compose up -d
docker compose ps

# LangGraph server (separate compose)
cd langgraph_workflows/dhg-agents-cloud
docker compose up -d

# Health checks
curl -s http://localhost:2026/ok          # LangGraph server
curl -s http://localhost:8011/healthz     # Registry API
curl -s http://localhost:3000             # Frontend
```

## Database migrations

The registry container runs `alembic upgrade head` on start (`registry/entrypoint.sh`).
Since PR #31 the chain replays on an empty database: 001 creates the `uuid-ossp`
and `vector` extensions, and revisions `002b_cme_bootstrap` / `002c_legacy_tables_bootstrap`
create the tables production originally got from hand-applied SQL. Both are guarded
per table and log what they skip, so an existing database is never touched. Two
tests keep it that way: `registry/test_alembic_literals.py` (no `text()` bind-parameter
tokens in raw SQL) and `registry/test_alembic_chain.py` (single head, linear chain).

To try a clean replay locally:

```bash
docker run -d --rm --name ci-sim-db -p 127.0.0.1:55432:5432 \
  -e POSTGRES_USER=dhg -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=dhg_registry pgvector/pgvector:pg15
docker run --rm --network host -v "$PWD":/w -w /w \
  -e DATABASE_URL=postgresql://dhg:testpass@127.0.0.1:55432/dhg_registry python:3.11 \
  bash -c 'pip install -q -r registry/requirements.txt pytest pytest-asyncio httpx && cd registry && alembic upgrade head && cd .. && pytest registry/ -q'
docker rm -f ci-sim-db
```

The container list on the [Service Inventory](./service-inventory.md) page is generated
from the compose files (`python3 scripts/generate-docs.py --write`) and checked in CI.

## Server

- **Host:** g700data1 (10.0.0.251)
- **OS:** Ubuntu 24.04
- **GPU:** NVIDIA RTX 5080 (16GB VRAM)
- **RAM:** 64GB
- **Docker:** 29.1.5
- **Storage:** 1.9TB root (12% used), 3.6TB data at /mnt/4tb (4% used)

## Repository

`https://github.com/sdnydude/dhgaifactory3.5.git` — Branch: master
