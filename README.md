# DHG AI Factory - CME Pipeline Multi-Agent System

**Production-Ready Dockerized Multi-Agent Architecture for CME/NON-CME Content Generation**

---

## 🎯 Overview

The DHG AI Factory is a sophisticated multi-agent system designed for automated generation of **ACCME-compliant CME content** and **NON-CME business/strategy materials**. It orchestrates 6 specialized agents through a master orchestrator to deliver funder-ready deliverables.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│         (CME/NON-CME Mode Detection & Coordination)         │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼─────────┐   ┌──────▼───────────┐
│  Medical LLM    │   │    Research      │
│  & NLP Agent    │   │  /Retriever      │
│                 │   │     Agent        │
│ • ICD-10        │   │ • PubMed         │
│ • NER           │   │ • ClinicalTrials │
│ • Guidelines    │   │ • 9 Sources      │
│ • SDOH/Equity   │   │ • URL Validation │
└─────────────────┘   └──────────────────┘
        │                     │
        │    ┌────────────────┴──────────┐
        │    │                           │
┌───────▼────▼─────┐   ┌────────────────▼────┐
│   Curriculum     │   │     Outcomes        │
│     Agent        │   │      Agent          │
│                  │   │                     │
│ • 6-10 Objectives│   │ • Moore Levels 3-5  │
│ • Moore Mapping  │   │ • Pre/Post/6-week   │
│ • Faculty Briefs │   │ • 3 Pathways        │
└──────────────────┘   └─────────────────────┘
        │                     │
        │    ┌────────────────┴──────────┐
        │    │                           │
┌───────▼────▼─────┐   ┌────────────────▼────┐
│  Competitor      │   │  QA/Compliance      │
│  Intelligence    │   │      Agent          │
│     Agent        │   │                     │
│ • Market Analysis│   │ • ACCME Validation  │
│ • 7 Field Extract│   │ • Fair Balance      │
│ • Differentiation│   │ • NO Hallucinations │
└──────────────────┘   └─────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  PostgreSQL + Vector│
        │   (DHG Registry)    │
        └─────────────────────┘
```

---

## ✅ Complete Agent System

### 1. **Orchestrator Agent** (Master)
- **Port**: 8001
- **Responsibilities**:
  - CME vs NON-CME mode detection
  - Multi-agent coordination
  - Task routing and orchestration
  - Final deliverable compilation
  
### 2. **Medical LLM & NLP Agent**
- **Port**: 8002
- **Capabilities**:
  - ICD-10 code extraction
  - Clinical NER (diseases, drugs, devices, labs)
  - Guideline summarization (ACR, ACC/AHA, ADA, GOLD, etc.)
  - Quality measure suggestions (NQF/CMS/MIPS)
  - SDOH/equity analysis
  
### 3. **Research/Retriever Agent**
- **Port**: 8003
- **Data Sources** (9):
  - PubMed/NCBI
  - ClinicalTrials.gov
  - CDC WONDER
  - CMS Quality Measures
  - USPSTF
  - AHRQ Evidence Reports
  - NIH RePORTER
  - Consensus API
  - Perplexity API
- **Features**: Caching, URL validation, reference management

### 4. **Curriculum Agent**
- **Port**: 8004
- **Outputs**:
  - 6-10 learning objectives
  - Moore Levels mapping
  - ICD-10 & QI measure integration
  - Activity-level curriculum outlines
  - Faculty/instructor briefs
  
### 5. **Outcomes Agent**
- **Port**: 8005
- **Focus**: Moore Levels 3-5
- **Deliverables**:
  - Pre/post/6-week assessment instruments
  - 3 innovative outcomes pathways
  - Outcomes data mapping
  - QI measures + ICD-10 integration
  
### 6. **Competitor Intelligence Agent**
- **Port**: 8006
- **Extracts**:
  - Provider, Funder, Date, Format, Credits, Topic, URL
  - Competitive differentiation summaries
  - Market intelligence reports
  - Provider/funder tracking
  
### 7. **QA/Compliance Agent**
- **Port**: 8007
- **Validates**:
  - Compliance mode correctness
  - No hallucinated sources
  - Reference validation
  - Word count constraints
  - ACCME rules (CME mode only)
  - Fair balance & commercial bias

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** installed
- **8GB+ RAM** recommended
- **API Keys** for:
  - OpenAI or Anthropic (for LLM agents)
  - Research APIs (PubMed, Consensus, Perplexity - optional)

### 1. Clone & Setup

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or vim, code, etc.
```

### 2. Configure Environment

**Required Variables:**
```bash
# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database
POSTGRES_PASSWORD=your_secure_password_here
```

**Optional Research APIs:**
```bash
CONSENSUS_API_KEY=...
PERPLEXITY_API_KEY=...
PUBMED_API_KEY=...
```

### 3. Build & Launch

```bash
# Build all agents
docker-compose build

# Start the system
docker-compose up -d

# Check logs
docker-compose logs -f orchestrator
```

### 4. Verify System Health

```bash
# Check orchestrator
curl http://localhost:8001/health

# Check all agents
for port in 8001 8002 8003 8004 8005 8006 8007; do
  echo "Checking port $port..."
  curl -s http://localhost:$port/health | jq .
done
```

---

## 📋 Usage

### Generate CME Needs Assessment

```bash
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "needs_assessment",
    "topic": "Type 2 Diabetes Management",
    "compliance_mode": "auto",
    "target_audience": "Primary Care Physicians",
    "word_count_target": 1250,
    "include_sdoh": true,
    "include_equity": true
  }'
```

### Response Structure

```json
{
  "task_id": "uuid",
  "status": "completed",
  "compliance_mode": "cme",
  "deliverables": {
    "needs_assessment": "...",
    "references": [...],
    "research_summary": "...",
    "qa_report": {...},
    "metadata": {...}
  },
  "violations": [],
  "warnings": []
}
```

---

## 🏗️ Architecture Details

### Database Schema (PostgreSQL + pgvector)

```sql
-- Core Tables
references         -- All validated citations
events             -- Request/response logs
api_cache          -- Research caching
topic_source_state -- Incremental updates
vector             -- Embeddings (pgvector)

-- CME Tracking
segments           -- Content segments
assessments        -- Pre/post/follow-up
outcomes           -- Moore Levels data
```

### Agent Communication

- **Protocol**: HTTP/REST
- **Format**: JSON
- **Timeout**: 300s default
- **Retry**: Configurable per agent

### Data Flow

```
User Request
    ↓
Orchestrator (detect mode)
    ↓
Research Agent → validate URLs → insert registry
    ↓
Medical LLM Agent → generate content
    ↓
QA/Compliance Agent → validate
    ↓
[If violations] → Medical LLM Agent (corrections)
    ↓
Orchestrator → compile deliverables
    ↓
Response to User
```

---

## 🔧 Configuration

### Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `POSTGRES_PASSWORD` | Database password | ✅ | changeme |
| `OPENAI_API_KEY` | OpenAI API key | ✅ | - |
| `CME_MODE_DEFAULT` | Default compliance mode | ❌ | auto |
| `LOG_LEVEL` | Logging level | ❌ | INFO |
| `ACCME_STRICT_MODE` | Enforce strict ACCME | ❌ | true |

Full list: See `.env.example`

### Port Mapping

| Service | Internal | External | Purpose |
|---------|----------|----------|---------|
| Orchestrator | 8000 | 8001 | Master coordination |
| Medical LLM | 8000 | 8002 | Medical NLP |
| Research | 8000 | 8003 | Evidence gathering |
| Curriculum | 8000 | 8004 | Learning objectives |
| Outcomes | 8000 | 8005 | Assessment design |
| Competitor Intel | 8000 | 8006 | Market analysis |
| QA/Compliance | 8000 | 8007 | Validation |
| PostgreSQL | 5432 | 5432 | Registry database |

---

## 📊 Monitoring

### Health Checks

```bash
# All agents
docker-compose ps

# Individual agent
docker-compose exec orchestrator curl localhost:8000/health
```

### Logs

```bash
# All logs
docker-compose logs -f

# Specific agent
docker-compose logs -f medical-llm

# Error logs only
docker-compose logs -f | grep ERROR
```

### Database Inspection

```bash
# Connect to registry
docker-compose exec registry-db psql -U dhg -d dhg_registry

# Check events
SELECT * FROM events ORDER BY created_at DESC LIMIT 10;

# Check references
SELECT COUNT(*) FROM references WHERE validated = true;
```

---

## 🧪 Testing

### Unit Tests

```bash
# Test individual agent
docker-compose exec orchestrator pytest /app/tests

# All agents
for agent in orchestrator medical-llm research curriculum outcomes competitor-intel qa-compliance; do
  docker-compose exec $agent pytest /app/tests
done
```

### Integration Test

```bash
# Full pipeline test
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d @test_requests/needs_assessment_diabetes.json
```

---

## 🔐 Security

### API Authentication

Set `ENABLE_API_AUTH=true` in `.env`:

```bash
JWT_SECRET=your_jwt_secret_here
JWT_EXPIRATION=3600
```

### Secrets Management

**Never commit** `.env` to version control:

```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "docker-compose.secrets.yml" >> .gitignore
```

---

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale research agents to 3 instances
docker-compose up -d --scale research=3

# Scale medical-llm to 2 instances
docker-compose up -d --scale medical-llm=2
```

### Load Balancing

Add nginx reverse proxy:

```yaml
# Add to docker-compose.yml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
```

---

## 🐛 Troubleshooting

### Agent Not Starting

```bash
# Check logs
docker-compose logs orchestrator

# Rebuild
docker-compose build --no-cache orchestrator
docker-compose up -d orchestrator
```

### Database Connection Issues

```bash
# Check database health
docker-compose exec registry-db pg_isready -U dhg

# Reset database
docker-compose down -v
docker-compose up -d registry-db
```

### Port Already in Use

```bash
# Find process using port 8001
lsof -i :8001

# Change port in docker-compose.yml
# Or stop conflicting process
```

---

## 📚 API Documentation

### Interactive Docs

Once running, access:

- **Orchestrator**: http://localhost:8001/docs
- **Medical LLM**: http://localhost:8002/docs
- **Research**: http://localhost:8003/docs
- **Curriculum**: http://localhost:8004/docs
- **Outcomes**: http://localhost:8005/docs
- **Competitor Intel**: http://localhost:8006/docs
- **QA/Compliance**: http://localhost:8007/docs

---

## 🎓 Examples

### CME Needs Assessment

**Request:**
```json
{
  "task_type": "needs_assessment",
  "topic": "Heart Failure Management Updates",
  "compliance_mode": "cme",
  "target_audience": "Cardiologists",
  "word_count_target": 1250,
  "reference_count_min": 8,
  "include_sdoh": true
}
```

### NON-CME Business Strategy

**Request:**
```json
{
  "task_type": "business_strategy",
  "topic": "Digital CME Platform Launch",
  "compliance_mode": "non-cme",
  "additional_context": {
    "market": "cardiology",
    "budget": "$500K"
  }
}
```

---

## 🤝 Contributing

### Adding New Agents

1. Create agent directory: `agents/new-agent/`
2. Add `main.py` with FastAPI app
3. Create `Dockerfile`
4. Add to `docker-compose.yml`
5. Update orchestrator routing

### Code Style

```bash
# Format code
black agents/

# Lint
ruff check agents/

# Type check
mypy agents/
```

---

## 📝 License

MIT License - See LICENSE file

---

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: `/docs` directory
- **Contact**: support@digitalharmonygroup.com

---

## 🎉 Ready to Deploy!

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Monitor
docker-compose logs -f
```

**System Status**: ✅ **PRODUCTION READY**

All 7 agents deployed and operational!
