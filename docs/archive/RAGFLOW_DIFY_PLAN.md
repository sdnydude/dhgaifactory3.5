# RAGFlow + Dify Installation Plan

## Research Findings (from GitHub docker-compose files)

> [!IMPORTANT]
> **RAGFlow uses MySQL, not PostgreSQL**. They cannot share CR database directly.

### Dify Dependencies
- **PostgreSQL** - metadata storage (can use external)
- **Redis** - celery broker, cache
- **Weaviate** - vector database for RAG
- **Nginx** - reverse proxy

### RAGFlow Dependencies
- **MySQL** - primary database (NOT PostgreSQL)
- **Elasticsearch** (in docker-compose-base.yml)
- **nginx** - web server

---

## Revised Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Dify (UI + Workflows)                   │
│                    Port 3000                               │
│   Uses: PostgreSQL + Redis + Weaviate                      │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│                    RAGFlow (Document Parsing)              │
│                    Port 9380                               │
│   Uses: MySQL + Elasticsearch                              │
└────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│             CR PostgreSQL (Antigravity Data)               │
│   antigravity_chats, messages, artifacts                   │
│   (Separate from Dify/RAGFlow - accessed via API)          │
└────────────────────────────────────────────────────────────┘
```

---

## Decision Required

**Option A: Use Dify Only**
- Simpler - one platform
- Has built-in vector DB (Weaviate)
- Can connect to external PostgreSQL (CR)
- Web scraper built-in
- **Recommendation if GraphRAG not critical**

**Option B: Use RAGFlow Only**
- Best document parsing
- Built-in GraphRAG
- Uses MySQL (separate from CR)
- More resource-heavy

**Option C: Use Both (Original Plan)**
- Complex - 10+ containers
- Two separate databases (MySQL + PostgreSQL)
- Integration via APIs, not shared DB
- Higher maintenance burden

---

## Ports (if using both)

| Service | Port | Database |
|---------|------|----------|
| Dify | 3000 | PostgreSQL (can be CR) |
| RAGFlow | 9380 | MySQL (separate) |
| Weaviate | 8080 | N/A |
| Redis | 6379 | N/A |

