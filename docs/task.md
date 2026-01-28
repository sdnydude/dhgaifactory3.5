# Knowledge Graph Implementation - Task Checklist

## Phase 1: pgvector Foundation (Week 1)

### Database Setup
- [ ] Enable pgvector extension on CR database
- [ ] Add vector columns to `antigravity_messages` and `antigravity_chats`
- [ ] Create vector indexes (IVFFlat for now)
- [ ] Test vector operations with sample data

### Auto-Vectorization
- [ ] Install sentence-transformers on server
- [ ] Create embedding generation function
- [ ] Add trigger for auto-vectorization on insert/update
- [ ] Backfill existing messages with embeddings

### Search API
- [ ] Create semantic search endpoint in registry-api
- [ ] Add hybrid search (vector + metadata filters)
- [ ] Test search performance (baseline metrics)
- [ ] Document API usage

---

## Phase 2: Onyx Integration (Week 2)

### Onyx Configuration
- [ ] Update Onyx docker-compose to use PostgreSQL backend
- [ ] Configure connection to CR database
- [ ] Test Onyx startup with PostgreSQL
- [ ] Verify Onyx creates its own tables in CR

### Data Integration
- [ ] Run Antigravity export ingestion to CR
- [ ] Verify Onyx can index CR data
- [ ] Test Onyx UI search functionality
- [ ] Configure Onyx connectors for automatic sync

### Validation
- [ ] Compare vector search results (direct vs Onyx)
- [ ] Verify no data duplication
- [ ] Load test with 1000+ sessions
- [ ] Document unified architecture

---

## Phase 3: LightRAG Integration (Week 3-4)

### LightRAG Setup
- [ ] Install LightRAG package on server
- [ ] Configure to use CR PostgreSQL backend
- [ ] Create knowledge graph schema in CR
- [ ] Test entity extraction on sample sessions

### Indexing
- [ ] Index first 100 Antigravity sessions
- [ ] Verify entity and relationship extraction
- [ ] Test community detection
- [ ] Measure indexing costs (track API usage)

### Query Interface
- [ ] Create smart routing layer (simple vs complex queries)
- [ ] Build multi-hop query examples
- [ ] Test cross-session pattern queries
- [ ] Benchmark query latency and accuracy

### Production Deployment
- [ ] Add LightRAG to production stack
- [ ] Configure background indexing for new sessions
- [ ] Set up monitoring and alerts
- [ ] Document query patterns

---

## Phase 4: Patent Documentation (Week 4-5)

### Workflow Documentation
- [ ] Document multi-agent coordination patterns
- [ ] Capture sub-agent spawning logic
- [ ] Map knowledge graph structure for CME domain
- [ ] Record cross-modal evidence synthesis workflow

### Patent Claims
- [ ] Draft claim: Multi-modal knowledge graph for CME
- [ ] Draft claim: Autonomous therapeutic area sub-agents
- [ ] Draft claim: Compliance pattern detection via graph
- [ ] Draft claim: Cross-program gap analysis automation

### Prior Art Research
- [ ] Search existing CME automation patents
- [ ] Search AI knowledge graph patents in healthcare
- [ ] Document novelty of combined approach
- [ ] Identify patentable differentiators

---

## Phase 5: Pharma Demo (Week 5-6)

### Demo Dataset
- [ ] Select 3-5 therapeutic areas with rich data
- [ ] Ensure diverse content types (video, podcast, slides, Q&A)
- [ ] Verify compliance examples are included
- [ ] Prepare competitor comparison data

### Demo Queries
- [ ] "What clinical gaps emerge across all diabetes programs?"
- [ ] "How do our oncology outcomes differ from competitors?"
- [ ] "What fair balance issues recur in cardiovascular CME?"
- [ ] "Connect physician questions to latest PubMed research"
- [ ] "Recommend 2026 content strategy for immunology"

### Presentation Materials
- [ ] Create demo script with live queries
- [ ] Prepare comparison: traditional vs GraphRAG results
- [ ] Show knowledge graph visualizations
- [ ] Document ROI metrics (time saved, quality improvement)

### Stakeholder Prep
- [ ] Identify target pharma client
- [ ] Schedule demo meeting
- [ ] Prepare Q&A for technical questions
- [ ] Draft follow-up engagement plan

---

## Success Metrics

### Technical
- [ ] Query latency <100ms p95 (vector search)
- [ ] Query latency <2s (complex GraphRAG queries)
- [ ] Index 1000+ sessions successfully
- [ ] <$1000 total LightRAG indexing cost

### Business
- [ ] 10+ unique multi-hop query examples
- [ ] 3+ patent-worthy workflow identifications
- [ ] 1 successful pharma demo completed
- [ ] Documented competitive advantage

---

## Risks & Mitigation

- **Risk**: LightRAG indexing costs exceed budget
  - **Mitigation**: Start with 100 sessions, measure costs, adjust scope

- **Risk**: Onyx PostgreSQL performance issues
  - **Mitigation**: Add pgvectorscale if needed, optimize indexes

- **Risk**: GraphRAG queries too slow for demo
  - **Mitigation**: Pre-compute common queries, use caching

- **Risk**: Patent claims overlap with existing work
  - **Mitigation**: Focus on CME-specific application, not general tech

---

## Backlog

### LibreChat Admin Dashboard
- [ ] Build admin UI integrated in LibreChat
- [ ] Natural language → SQL query interface
- [ ] Local LLM (Qwen/Ollama) for query generation
- [ ] Database visualization and results display
- [ ] Access control for admin users

---

## Next Major Goal: Antigravity Sync Agent (LangGraph Cloud)

**Schedule:** 4am, 12pm, 7pm daily

### Agent Tasks
- [ ] Download/sync Antigravity .pb files
- [ ] Convert .pb → .md (parse conversations)
- [ ] Ingest new messages into CR database
- [ ] Process and link artifacts
- [ ] Generate embeddings for new content

### Pipeline Documentation (to be tracked)
- **Extraction Method:** Local API via CSRF token (port 58575)
- **Endpoints Used:** GetAllCascadeTrajectories, GetCascadeTrajectory
- **Output Format:** JSON with session_id, messages[], artifacts[]
- **Database Tables:** antigravity_artifacts, antigravity_messages (pending)

---

## Backlog

### Ingest All Outlines to Database
- [ ] Add all artifact outlines (task.md, implementation plans, etc.) to CR as source documents
- [ ] Make them searchable for context retrieval

