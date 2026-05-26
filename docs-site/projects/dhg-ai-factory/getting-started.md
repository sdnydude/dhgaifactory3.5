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

## Server

- **Host:** g700data1 (10.0.0.251)
- **OS:** Ubuntu 24.04
- **GPU:** NVIDIA RTX 5080 (16GB VRAM)
- **RAM:** 64GB
- **Docker:** 29.1.5
- **Storage:** 1.9TB root (12% used), 3.6TB data at /mnt/4tb (4% used)

## Repository

`https://github.com/sdnydude/dhgaifactory3.5.git` — Branch: master
