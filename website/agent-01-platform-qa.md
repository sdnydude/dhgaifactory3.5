# Agent 1: DHG AI Factory — Platform Q&A Agent
## Full Production Build Prompt for Gemini

---

**Build a complete, production-ready conversational Q&A agent for the DHG AI Factory platform. This agent replaces a traditional FAQ page and serves as living proof of DHG's AI capabilities. Every file must be complete — no placeholders, no truncated code, no TODOs, no "implement here" comments. If a file exceeds output limits, split into multiple responses but deliver every line.**

---

## Architecture

```
dhg-qa-agent/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry
│   ├── config.py                # Environment and settings management
│   ├── models.py                # Pydantic request/response models
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py             # LangGraph orchestration graph
│   │   ├── nodes.py             # All graph node functions
│   │   ├── state.py             # Graph state definition
│   │   ├── prompts.py           # All system prompts and templates
│   │   └── tools.py             # Agent tool definitions
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── loader.py            # Document ingestion pipeline
│   │   ├── embeddings.py        # Embedding generation and management
│   │   ├── retriever.py         # Vector search and retrieval
│   │   └── chunks.py            # Text chunking strategies
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── conversation.py      # Conversation history management
│   │   └── session.py           # Session state persistence
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py            # API endpoint definitions
│   │   ├── websocket.py         # WebSocket handler for streaming
│   │   └── middleware.py        # CORS, rate limiting, logging
│   └── utils/
│       ├── __init__.py
│       ├── logging.py           # Structured logging configuration
│       └── metrics.py           # Prometheus metrics
├── frontend/
│   ├── index.html               # Embeddable chat widget — full glassmorphism UI
│   ├── chat-widget.js           # Complete frontend JS — no framework dependencies
│   └── chat-widget.css          # DHG glassmorphism styles
├── knowledge_base/
│   ├── platform_overview.md     # What is the AI Factory
│   ├── architecture.md          # How it works — modules, orchestration, containers
│   ├── capabilities.md          # What it can do — per module
│   ├── use_cases.md             # Industry and business use cases
│   ├── technical_specs.md       # Stack, requirements, deployment
│   ├── pricing_model.md         # Licensing, tiers, engagement models
│   ├── faq.md                   # Common questions and answers
│   ├── company_overview.md      # DHG divisions, history, leadership
│   └── differentiators.md       # Why AI Factory vs alternatives
├── scripts/
│   ├── ingest.py                # Knowledge base ingestion script
│   └── test_agent.py            # End-to-end agent test suite
└── tests/
    ├── __init__.py
    ├── test_retriever.py
    ├── test_graph.py
    └── test_api.py
```

---

## Technical Stack

- **Runtime:** Python 3.11+
- **Framework:** FastAPI with uvicorn
- **Orchestration:** LangGraph (NOT LangChain agents — use LangGraph's StateGraph explicitly)
- **LLM:** Google Gemini 2.5 Pro via `google-genai` SDK (primary), with fallback support for Anthropic Claude via `anthropic` SDK
- **Embeddings:** Google text-embedding-004 via `google-genai`
- **Vector Store:** ChromaDB (persistent, Docker volume mounted)
- **Streaming:** WebSocket for real-time token streaming to frontend
- **Containerization:** Docker with docker-compose
- **Monitoring:** Prometheus metrics endpoint + structured JSON logging

---

## Detailed Specifications

### 1. FastAPI Application (`app/main.py`)

```python
# Requirements:
# - FastAPI app with lifespan handler for startup/shutdown
# - On startup: load knowledge base, initialize ChromaDB, build LangGraph
# - Health check endpoint at /health
# - Prometheus metrics endpoint at /metrics
# - Mount static files for frontend widget
# - CORS middleware configured for embedding on any DHG domain
# - Request ID middleware for tracing
# - Rate limiting: 30 requests/minute per IP for chat, 5/minute for WebSocket connections
```

### 2. LangGraph Orchestration (`app/agent/graph.py`)

Build a StateGraph with these nodes:

```
START → classify_intent → route
  ├── retrieve_knowledge → generate_response → format_output → END
  ├── handle_greeting → END
  ├── handle_off_topic → END
  └── handle_clarification → generate_clarifying_question → END
```

**Nodes:**

- `classify_intent`: Determine if the query is a platform question, greeting, off-topic, or needs clarification. Use a structured Gemini call with enum output.
- `retrieve_knowledge`: Query ChromaDB with the user's question. Use hybrid search — semantic similarity + keyword matching. Return top 5 chunks with relevance scores.
- `generate_response`: Compose answer using retrieved context + conversation history. System prompt enforces DHG brand voice: professional, confident, knowledgeable, never salesy. Must cite which knowledge base document the answer came from.
- `format_output`: Structure the response with optional follow-up suggestions (max 3 clickable questions the user might ask next).
- `handle_greeting`: Warm, branded greeting. Introduce itself as the AI Factory Assistant. Suggest 3 starter questions.
- `handle_off_topic`: Politely redirect. Acknowledge the question, explain its scope, offer to help with platform-related questions.
- `handle_clarification`: When the query is ambiguous, generate a targeted clarifying question rather than guessing.

**State Schema:**
```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str
    intent: str  # "platform_question" | "greeting" | "off_topic" | "needs_clarification"
    retrieved_chunks: list[dict]  # {content, source, score}
    response: str
    follow_up_suggestions: list[str]
    session_id: str
    turn_count: int
    confidence_score: float
```

### 3. Knowledge Base System (`app/knowledge/`)

**Loader (`loader.py`):**
- Read all markdown files from `knowledge_base/` directory
- Parse with frontmatter support (title, category, last_updated)
- Split into chunks using recursive character splitter: 800 tokens, 100 token overlap
- Preserve document metadata through chunking
- Generate unique chunk IDs based on document + position

**Embeddings (`embeddings.py`):**
- Use Google text-embedding-004 model
- Batch embedding generation (max 100 chunks per batch)
- Cache embeddings to avoid regeneration on restart
- Dimensionality: 768

**Retriever (`retriever.py`):**
- ChromaDB collection with HNSW index
- Hybrid search: cosine similarity on embeddings + BM25 keyword match
- Re-ranking: combine scores with weighted average (0.7 semantic, 0.3 keyword)
- Return top 5 results with scores
- Minimum relevance threshold: 0.35 — below this, trigger "I don't have information on that" response
- Include source document attribution in results

### 4. Conversation Memory (`app/memory/`)

- Store conversation history per session (session_id from cookie or header)
- Keep last 10 turns in active context window
- Summarize older turns into a rolling summary using Gemini
- Session timeout: 30 minutes of inactivity
- Store in-memory with optional Redis backend (env flag)
- Conversation export endpoint for analytics

### 5. API Endpoints (`app/api/routes.py`)

```
POST /api/chat
  Body: { "message": str, "session_id": str | null }
  Response: { "response": str, "suggestions": list[str], "sources": list[str], "session_id": str, "confidence": float }

GET /api/chat/stream (WebSocket)
  Connect with session_id query param
  Send: { "message": str }
  Receive: { "type": "token" | "sources" | "suggestions" | "done", "data": str | list }

GET /api/health
  Response: { "status": "healthy", "version": str, "knowledge_base_docs": int, "uptime_seconds": float }

GET /api/metrics
  Prometheus format metrics

POST /api/feedback
  Body: { "session_id": str, "message_id": str, "rating": "up" | "down", "comment": str | null }
```

### 6. Frontend Chat Widget (`frontend/`)

Build a complete, self-contained chat widget that can be embedded via a single `<script>` tag on any page.

**Features:**
- Glassmorphism design matching DHG Apple aesthetic
- Floating chat bubble (bottom-right) with DHG Orange gradient
- Expands to full chat panel on click
- Real-time streaming via WebSocket — tokens appear as they generate
- Clickable follow-up suggestion pills below each response
- Source attribution links at bottom of responses
- Typing indicator with animated dots
- Message history preserved in session
- Thumbs up/down feedback buttons on each response
- Mobile responsive — full-screen on mobile
- Smooth open/close animations
- Keyboard accessible (Enter to send, Escape to close)
- Dark mode by default (matches glassmorphism site)

**DHG Glassmorphism CSS:**
```css
/* Chat panel */
backdrop-filter: blur(20px);
background: rgba(50, 55, 74, 0.85);
border: 1px solid rgba(255, 255, 255, 0.08);
border-radius: 20px;
box-shadow: 0 16px 48px rgba(0, 0, 0, 0.3);

/* User message bubbles */
background: linear-gradient(135deg, var(--dhg-purple), #7a42b8);
border-radius: 18px 18px 4px 18px;

/* Agent message bubbles */
background: rgba(255, 255, 255, 0.06);
border: 1px solid rgba(255, 255, 255, 0.06);
border-radius: 18px 18px 18px 4px;

/* Suggestion pills */
background: rgba(102, 51, 153, 0.15);
border: 1px solid rgba(102, 51, 153, 0.3);
border-radius: 20px;

/* Input field */
background: rgba(255, 255, 255, 0.05);
border: 1px solid rgba(255, 255, 255, 0.1);
border-radius: 12px;
```

**Embed Code (what site owners paste):**
```html
<script src="https://your-domain.com/chat-widget.js" data-agent="qa" data-theme="dark"></script>
```

The JS file must:
- Create its own shadow DOM to avoid CSS conflicts
- Inject all styles internally
- Connect to WebSocket on first interaction (lazy connection)
- Handle reconnection with exponential backoff
- Be under 50KB minified

### 7. System Prompts (`app/agent/prompts.py`)

**Main QA System Prompt:**
```
You are the DHG AI Factory Assistant — a knowledgeable, professional guide to Digital Harmony Group's AI Factory platform.

IDENTITY:
- You represent DHG, a technology holding company led by CEO Stephen Webber
- You are an expert on the AI Factory: its architecture, capabilities, use cases, and value proposition
- You speak with confidence and authority, but never arrogance
- Your tone is professional, warm, and direct — like a senior solutions engineer at a Fortune 500 company

BEHAVIOR RULES:
- ONLY answer questions about the DHG AI Factory, DHG as a company, and related capabilities
- ALWAYS ground your answers in the provided knowledge base context
- If the knowledge base doesn't contain the answer, say so honestly and suggest contacting DHG directly
- NEVER fabricate features, pricing, or capabilities not in the knowledge base
- NEVER discuss competitors by name — focus on DHG's strengths
- When asked about pricing, provide what's in the knowledge base and suggest a consultation for custom quotes
- Suggest relevant follow-up questions to guide the conversation deeper
- Keep responses concise (2-4 paragraphs max) unless the user asks for detail
- Use concrete examples and analogies to explain technical concepts to non-technical audiences
- Always attribute information to its source document

FORMATTING:
- Use markdown formatting for readability
- Bold key terms on first mention
- Use bullet points sparingly — prefer prose
- End with 1-3 suggested follow-up questions when appropriate
```

### 8. Knowledge Base Content (`knowledge_base/`)

Create comprehensive, realistic content for each file. Each document should be 800-1500 words with proper frontmatter. The content should describe a modular AI platform built on Docker containers and LangGraph orchestration that can adapt to any business need. Cover:

- **platform_overview.md**: Vision, mission, what makes it different. The "factory" metaphor — modular production lines for AI workflows.
- **architecture.md**: Docker containers as modules, LangGraph as orchestration brain, API gateway, observability stack (Prometheus/Grafana), secrets management (Infisical vault).
- **capabilities.md**: Document processing, conversational AI, workflow automation, content generation, data analysis, integration hub. Each as a module.
- **use_cases.md**: Healthcare/CME, financial services, media production, enterprise operations, customer service. Real-world scenarios.
- **technical_specs.md**: Python 3.11+, Docker, LangGraph, supported LLMs (Gemini, Claude, GPT-4), vector stores, GPU requirements, deployment options.
- **pricing_model.md**: Starter, Professional, Enterprise tiers. Module-based pricing. Custom development at $450/hour.
- **faq.md**: 20 common questions with thorough answers covering security, deployment, customization, support, SLAs.
- **company_overview.md**: DHG divisions (DHG CME, DHG Studios, DHG AI, DHG Productions, Streamcubation), 35 years experience, Stephen Webber CEO.
- **differentiators.md**: Modular vs monolithic, general-purpose vs niche, enterprise-grade observability, Fortune 500 quality standards.

### 9. Docker Configuration

**Dockerfile:**
- Python 3.11-slim base
- Install dependencies from requirements.txt
- Copy application code
- Expose port 8000
- Health check with curl to /api/health
- Run with uvicorn, 4 workers, host 0.0.0.0

**docker-compose.yml:**
- `qa-agent` service: build context, port 8000, env_file, volume for ChromaDB persistence, volume for knowledge_base
- `chromadb` service: chromadb/chroma image, port 8001, persistent volume
- Named volumes for data persistence
- Network isolation
- Restart policy: unless-stopped
- Resource limits: 2GB RAM, 1 CPU for agent; 1GB RAM for ChromaDB

### 10. Testing (`scripts/test_agent.py` and `tests/`)

**End-to-end test script** that:
- Sends 20 diverse test queries covering all intent types
- Validates response structure
- Checks that source attribution is present
- Measures response latency
- Tests conversation continuity (multi-turn)
- Tests off-topic handling
- Tests edge cases (empty input, very long input, special characters)
- Outputs results as a formatted report

**Unit tests:**
- `test_retriever.py`: Test chunking, embedding, search accuracy, relevance thresholds
- `test_graph.py`: Test each node independently, test routing logic, test state transitions
- `test_api.py`: Test all endpoints, test rate limiting, test WebSocket connection

### 11. requirements.txt

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
google-genai==1.1.0
anthropic==0.42.0
langgraph==0.2.60
langchain-core==0.3.28
chromadb==0.5.23
pydantic==2.10.4
pydantic-settings==2.7.1
python-multipart==0.0.19
websockets==14.1
prometheus-client==0.21.1
httpx==0.28.1
python-dotenv==1.0.1
structlog==24.4.0
rank-bm25==0.2.2
tiktoken==0.8.0
pytest==8.3.4
pytest-asyncio==0.25.0
```

---

## Critical Requirements

1. **EVERY file must be complete and production-ready.** No `# TODO`, no `pass`, no `...`, no `# implement this`. Every function must have full implementation.
2. **If output exceeds response limits, say "CONTINUED IN NEXT RESPONSE" and continue seamlessly.** Number each continuation (Part 1/N, Part 2/N, etc.).
3. **All error handling must be explicit** — try/except with structured logging, never silent failures.
4. **All configuration via environment variables** — .env.example must document every variable with descriptions and example values.
5. **The frontend widget must work standalone** — paste the script tag on any HTML page and it works with zero additional setup.
6. **The knowledge base content must be substantive and realistic** — not lorem ipsum, not skeleton content. Real descriptions of a real AI platform.

---

## Verification Checklist

Before delivering, confirm:
- [ ] `docker-compose up` starts all services with zero errors
- [ ] Knowledge base ingestion completes and populates ChromaDB
- [ ] POST /api/chat returns structured responses with sources
- [ ] WebSocket streaming delivers tokens in real-time
- [ ] Frontend widget renders correctly and connects to backend
- [ ] All 20 test queries pass with appropriate responses
- [ ] Off-topic queries are handled gracefully
- [ ] Rate limiting works correctly
- [ ] Health check returns accurate system status
- [ ] Prometheus metrics are exposed and accurate

---
