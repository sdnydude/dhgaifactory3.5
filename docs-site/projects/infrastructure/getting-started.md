---
sidebar_position: 1
title: Getting Started
---

# Infrastructure

Cross-cutting infrastructure that every DHG project depends on — the pieces that
aren't owned by any single app but underpin all of them.

<img src="/img/infrastructure/doppler-architecture.svg" alt="DHG Doppler architecture: Doppler Cloud projects (portage, aifactory, dhg-infra shared, and 5 more) each with dev/stg/prd configs feeding secrets at runtime to g700data1 CLI, server 2 CLI, and CF Workers API" style={{maxWidth: '720px', width: '100%'}} />

## What's here

| Topic | Covers |
|-------|--------|
| [Doppler — Secrets Management](./doppler.md) | Single source of truth for every secret across all DHG projects: CLI, environments, the `.env` model, and Claude Code integration. |

More infrastructure docs (Cloudflare tunnel, observability stack) will land here as
they're written.
