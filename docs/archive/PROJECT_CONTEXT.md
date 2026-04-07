# DHG AI Factory - Project Context

**Last Updated:** January 14, 2026  
**Server:** 10.0.0.251 (Ubuntu, RTX 5080)  
**Branch:** feature/librechat-integration

---

## Project Path
```
/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/
```

## Repository
- **Remote:** https://github.com/sdnydude/dhgaifactory3.5.git
- **Active Branch:** feature/librechat-integration (all LibreChat/Infisical work here)
- **Master Branch:** production-stable

## Infrastructure
- **PostgreSQL + pgvector:** 14 tables, vector embeddings
- **Docker Compose:** 25+ containers
- **LibreChat:** Port 3010 (Dark theme, Ollama integration)
- **Infisical:** Port 8080 (secrets.digitalharmonyai.com)
- **LangGraph:** Port 2024 (orchestrator API at 8011)

## Active Services (Verified Healthy)
- Medical-LLM (Ollama medllama2)
- Research, Curriculum, Outcomes
- Competitor-Intel, QA-Compliance
- Visuals (image generation)
- Orchestrator (LangGraph workflow coordination)

## Key Decisions
1. LibreChat as primary chat UI
2. All agents in code (not Agent Builder)
3. MCP integration enabled
4. Shared central PostgreSQL registry
5. Distributed GPU: .251 (5080), ASUS laptop (5090), Ubuntu PC (4080)

## SSH Access
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251
```

## Quick Commands
```bash
# Check services
docker compose ps

# View logs
docker compose logs -f dhg-orchestrator

# Git status
git status --short
```
