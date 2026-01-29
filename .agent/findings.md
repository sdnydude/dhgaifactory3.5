# Findings: DHG AI Factory Research

## Platform Architecture

| Platform | Role | Status | Port |
|----------|------|--------|------|
| LibreChat | Chat UI | Running | :3010 |
| Dify | Workflow builder | Running | :3000 |
| RAGFlow | Enterprise RAG | Running | :8585 |
| LangSmith | Agent tracing | Cloud | N/A |
| Ollama | Local LLM | Running | :11434 |

## Agent Services

| Agent | Port | Purpose | Status |
|-------|------|---------|--------|
| dhg-registry-api | 8011 | Central registry | Healthy |
| dhg-research | 8003 | CME research | To verify |
| dhg-curriculum | 8004 | Curriculum dev | Available |
| dhg-outcomes | 8005 | Outcomes tracking | Available |
| dhg-competitor-intel | 8006 | Competitor intel | Available |
| dhg-qa-compliance | 8007 | QA/compliance | Available |

## Database State

- **CR Database:** PostgreSQL on .251
- **antigravity_messages:** 4,974 total, 4,712 with embeddings
- **Vector dimension:** 384 (MiniLM)

## Skills Installed

1. **antigravity-awesome-skills** (552+ domain skills)
2. **planning-with-files** (persistent context pattern)

## Key Files

- `/docs/FRONT_FACING_AGENTS_PLAN.md` - Implementation plan
- `/docs/STACK_SPEC.md` - Full infrastructure spec
- `/.agent/rules/mandatory-context.md` - Context enforcement
- `/.agent/workflows/pre-response.md` - Pre-response checklist

## Research Notes

### RAGFlow Integration
- Google OAuth configured
- Redis connected
- Accessible at ragflow.digitalharmonyai.com
- Needs: LLM connection, knowledge base creation

### CME Research Agent
- Existing at :8003
- Has output templates (cme-agent-context.md)
- Needs: RAG integration, LibreChat form
