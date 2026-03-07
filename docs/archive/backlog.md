# Build Later Backlog

**Last Updated:** Jan 25, 2026

---

## P1 - High Value (Next Up)

| Item | Why |
|------|-----|
| **Multi-provider BYOK integration** | Users add their own API keys for ChatGPT, Claude, Gemini, etc. |
| **Chat import pipeline** | Import 1000s Claude/ChatGPT/Gemini sessions |
| **MemoRAG deployment** | Cross-session memory with corpus |
| **CME video transcription** | 300 hours → searchable text |
| **GraphRAG for medical content** | Entity relationships, multi-hop reasoning |

---

## P2 - Medium Value

| Item | Why |
|------|-----|
| **Email import with filtering** | Selective ingestion from 24yr archive |
| **Embedding generation on insert** | Auto-vectorize new content |
| **Marketing analysis pipeline** | Campaign → company performance correlation |
| **LangSmith evaluators** | Quality gates for CME Research Agent |

---

## P3 - Nice to Have

| Item | Why |
|------|-----|
| **NAS document triage** | 35TB selective ingestion |
| **Company signals table** | Stock/news correlation with campaigns |
| **Multi-audience assistants** | Physician/nurse/patient variants |
| **LangSmith automations** | Auto dataset building, error alerts |

---

## Ideas Captured (Not Prioritized)

- Study spam corpus for marketing innovation
- Connect campaigns to company/product performance over time
- Speaker detection in CME videos (who said what)
- pg_vectorize for auto-embedding

---

## Completed

- [x] Fix registry-api Docker (missing files)
- [x] Fix database.py connection string
- [x] Fix Pydantic UUID schema
- [x] LangSmith Cloud deployment with secrets
- [x] Add antigravity_chats storage (2 rows saved)

---

## P2 - Added Jan 27, 2026

| Item | Why |
|------|-----|
| **Slack Integration** | Create DHG AI Factory Bot with channels:manage, chat:write scopes. Set up #alerts-critical, #dev-activity, #agent-traces for Alertmanager and GitHub notifications. CLI installed on .251, needs full Bot Token. |
