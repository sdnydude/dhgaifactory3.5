# DHG AI Factory v3.5 — CLAUDE.md

ATTENTION: Loaded every session, re-anchored post-compaction — present every turn. Every word costs tokens. Be dense. If task doesn't match directive, skip. Conflicts resolved: 1) Security 2) Production state 3) Architecture 4) Brand.

IDENTITY: Sole AI dev partner for DHG AI Factory. Pharma-grade CME grant docs. General-purpose modular enterprise AI — CME ~10% revenue. CME mode ONLY on explicit Stephen toggle. Fortune 500 quality bar.

SERVER: g700data1 (10.0.0.251), Ubuntu 24.04, Docker 29.1.5, RTX 5080 (16GB VRAM), 64GB RAM, 1.9TB (11% used).

REPO: https://github.com/sdnydude/dhgaifactory3.5.git — branch: master.

VERSION PINS (stack itself is in global CLAUDE.md): SQLAlchemy 2.0, Pydantic 2.5, PostgreSQL 15, Docker 29.1.5.

KEY PATHS:
langgraph_workflows/dhg-agents-cloud/src/*.py (agents)
langgraph_workflows/dhg-agents-cloud/src/orchestrator.py (1408 lines)
langgraph_workflows/dhg-agents-cloud/langgraph.json (registered graphs)
registry/api.py (registry API)
registry/cme_endpoints.py (990 lines)
registry/models.py (DB models)
web-ui/src/ (legacy — broken, do not fix)
docker-compose.yml (main)
docker-compose.override.yml (override — hardcoded secrets, see C11)

ARCH: 13 agent graphs + 4 orchestrator graphs (needs_package, curriculum_package, grant_package, full_pipeline). Each: TypedDict state, ChatAnthropic, @traceable, asyncio.wait_for (5min), retry (3 max).

CONSTRAINTS:
- LangGraph server: separate Docker network (host.docker.internal). No cross-container comms without explicit config.
- Web-UI cannot invoke LangGraph. Broken. Do not fix — replace.
- CME compliance: Stephen toggle ONLY.
- Version control = sole source of truth. Sequential phases. No overlapping work.
- No silent refactors. No behavior changes without rationale.
- Written change request required. Map to phase + acceptance criteria.

NOT IN USE (DO NOT SUGGEST): Node-RED (deprecated). Zapier. On24. Legacy web-ui WebSocket (replacing). Infisical (crash-looping).

AUDIT: 2026-07-02. Review: when graphs added/removed.
