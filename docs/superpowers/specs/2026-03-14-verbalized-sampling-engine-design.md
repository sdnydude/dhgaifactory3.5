# Verbalized Sampling Engine — Design Spec

**Date:** 2026-03-14
**Author:** Stephen Webber + Claude
**Status:** Draft — pending review
**Branch:** feature/langgraph-migration

---

## 1. Problem Statement

Aligned LLMs suffer from mode collapse — RLHF training narrows their output distributions, causing them to converge on a single "safe" response rather than exploring the full solution space. This is structurally incompatible with the DHG AI Factory's CME pipeline, which IS a divergent-convergent system: brainstorming needs diverse options, gap analysis needs multiple perspectives, quality review needs varied critiques, and human reviewers need real alternatives — not three paraphrases of the same answer.

Verbalized Sampling (VS), from CHATS-Lab (arXiv 2510.01171, Apache 2.0), solves this by asking LLMs to generate multiple responses with self-assigned probability distributions, then sampling from that distribution. The tau parameter forces tail sampling — each response must have probability below tau, preventing any single response from dominating.

## 2. Solution Overview

A standalone Docker service (`dhg-vs-engine`, port 8013) that provides divergent generation as an API. Any system in the DHG stack — LangGraph agents, the `/ship` workflow, future projects — can call it to generate diverse outputs with probability distributions, then select from them via argmax, weighted sampling, or human choice.

The service ports ~650 lines from the CHATS-lab reference implementation: core distribution math (~300 lines from `selection.py`) and evaluation framework (~350 lines from `analysis/evals/`). It manages its own LLM connections (Ollama for local, Anthropic API for cloud, OpenAI-compatible for future providers) and provides built-in benchmarking via DiversityEvaluator and TTCTEvaluator — academically standard metrics for proving VS works.

Stephen's framing: **"This is a critical tool for divergent convergence."** VS is structural, not optional — it provides the mechanical foundation for the divergent half of the CME pipeline.

## 3. Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | VS scope | Both agent-level AND orchestrator-level | Nested divergent-convergent system: agents diverge internally (e.g., 5 gap analysis approaches), orchestrator diverges across agents (e.g., 3 quality review strategies). Each level converges independently before feeding the next. |
| D2 | Probability framing | `confidence` (default, overridable) | VS supports 7 framings (confidence, likelihood, probability, etc.). `confidence` is most intuitive for human reviewers seeing badges. Overridable per request for experimentation. |
| D3 | Default parameters | `tau <= 0.10`, `min_p=0.03`, `k=3-5` per phase | Two-parameter design matching CHATS-lab: `tau` is a soft prompt ceiling nudging the LLM toward uniform distribution (each response's confidence near 1/k). `min_probability` is a postprocessing floor (from CHATS-lab's `tau` parameter) that filters out responses the LLM self-rated as junk. `repair_weight()` normalizes whatever remains. k=3-5 balances diversity against cost. |
| D4 | Parameter override | All parameters overridable per API call | Phase defaults are sensible starting points; callers can tune k, tau, model, and framing per request for specific use cases. |
| D5 | Human presentation | Top 3 after quality gate filtering (from k=5 generated) | Generate 5 for diversity headroom, filter by quality score, present top 3 to humans. Humans see curated quality; the system gets full exploration. |
| D6 | UX pattern | Auto-select one + "show alternatives" expands to unordered cards with confidence badges | Mitigates center-stage bias (Stephen: "if we present three, most people will pick the one presented number 2"). Auto-select uses VS probability-weighted sampling. Cards are unordered with badges (conventional/novel/exploratory), not numbered lists. |
| D7 | Implementation | Standalone Docker service (FastAPI, port 8013) | NOT a Python library. Docker module can be bolted onto AI Factory and future projects. Matches existing service patterns (registry-api on 8011, session-logger on 8009). |
| D8 | LLM strategy | Service manages all LLM connections | Supports Ollama (local-first), Anthropic API (cloud), and OpenAI-compatible endpoints. Local AI first strategy must be preserved — never couple to a single provider. |
| D9 | Portability | Bolt-on Docker module | Designed for reuse across AI Factory and future DHG projects. Self-contained with its own Dockerfile, requirements, health check, and Prometheus metrics. |

## 4. Architecture

### 4.1 System Context

```
┌─────────────────────────────────────────────────────────┐
│                    DHG AI Factory                         │
│                                                           │
│  ┌──────────────┐    POST /vs/generate    ┌────────────┐ │
│  │  LangGraph   │ ─────────────────────── │            │ │
│  │  Agents      │                         │  dhg-vs-   │ │
│  │  (Cloud)     │ ◄───────────────────── │  engine    │ │
│  └──────────────┘    DiscreteDist resp    │  :8013     │ │
│                                           │            │ │
│  ┌──────────────┐    POST /vs/generate    │            │ │
│  │  /ship       │ ─────────────────────── │  ┌──────┐  │ │
│  │  workflow    │                         │  │ LLM  │  │ │
│  │  (Claude     │ ◄───────────────────── │  │Router│  │ │
│  │   Code)      │    DiscreteDist resp    │  └──┬───┘  │ │
│  └──────────────┘                         │     │      │ │
│                                           └─────┼──────┘ │
│                                                 │        │
│                    ┌────────────────────────────┤        │
│                    │            │               │        │
│               ┌────▼───┐  ┌────▼─────┐  ┌─────▼─────┐  │
│               │ Ollama │  │Anthropic │  │ OpenAI-   │  │
│               │ :11434 │  │  API     │  │ compat    │  │
│               └────────┘  └──────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Service Components

| Component | Responsibility |
|-----------|---------------|
| **FastAPI app** | HTTP server, request validation, Prometheus metrics |
| **LLM Router** | Model selection — routes to Ollama, Anthropic, or OpenAI-compatible based on request `model` field |
| **VS Prompt Builder** | Constructs the VS prompt with k, tau, framing, and format instructions |
| **Distribution Parser** | Parses LLM response into structured `DiscreteDist` — handles malformed outputs via `repair_weight()` |
| **Selection Engine** | Implements argmax, weighted sample, and filter+reweight strategies |

### 4.3 Docker Integration

Container name: `dhg-vs-engine`
Port: `8013:8000`
Network: `dhgaifactory35_dhg-network`

```yaml
# Addition to docker-compose.override.yml (matches session-logger, logo-maker pattern)
vs-engine:
  build:
    context: ./services/vs-engine
    dockerfile: Dockerfile
  container_name: dhg-vs-engine
  environment:
    - OLLAMA_BASE_URL=http://dhg-ollama:11434
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    - LOG_LEVEL=${LOG_LEVEL:-INFO}
  ports:
    - "8013:8000"
  labels:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 5s
    retries: 3
  networks:
    - dhg-network
  restart: unless-stopped
  depends_on:
    ollama:
      condition: service_started
```

### 4.4 Cloud Connectivity (LangGraph Cloud → VS Engine)

LangGraph agents run in the cloud at `*.us.langgraph.app`. They reach local services through the existing Cloudflare tunnel (ID: `30437aa6`), the same mechanism used for `AI_FACTORY_REGISTRY_URL`.

**Cloudflare tunnel route** (add to `/etc/cloudflared/config.yml`):

```yaml
- hostname: vs.digitalharmonyai.com
  service: http://localhost:8013
```

**Environment variable** for LangGraph Cloud agents:

```
VS_ENGINE_URL=https://vs.digitalharmonyai.com
```

LangGraph agent code uses `os.getenv("VS_ENGINE_URL", "http://dhg-vs-engine:8000")` — defaults to Docker networking for local dev, overridden to the tunnel URL in cloud deployment. Same pattern as `AI_FACTORY_REGISTRY_URL`.

Cloudflare Access + Google OAuth (already configured on `digitalharmonyai.com`) provides authentication. No additional auth layer needed.

### 4.5 File Layout

```
services/vs-engine/
├── Dockerfile
├── requirements.txt
├── main.py                  # FastAPI app, routes, health, metrics
├── config.py                # Phase defaults, environment loading
├── llm_router.py            # LLM connection management (Ollama, Anthropic, OpenAI)
├── prompt_builder.py        # VS prompt construction (k, tau, framing, format)
├── distribution.py          # Item, DiscreteDist, repair_weight, postprocess_responses
├── selection.py             # argmax, sample, filter_reweight strategies
└── tests/
    ├── test_distribution.py # Unit tests for core math
    ├── test_prompt.py       # Prompt construction tests
    ├── test_selection.py    # Selection strategy tests
    └── test_api.py          # Integration tests
```

## 5. Core Math (Ported from CHATS-lab)

The following structures and functions are ported from `verbalized_sampling/selection.py` (~300 lines). All ported code retains Apache 2.0 license headers crediting CHATS-lab.

### 5.1 Data Structures

```python
@dataclass
class Item:
    """A single generated response with its probability."""
    content: str
    probability: float
    metadata: dict  # quality_score, label (conventional/novel/exploratory), etc.

@dataclass
class DiscreteDist:
    """A discrete probability distribution over generated responses."""
    items: list[Item]           # sorted descending by probability
    distribution_id: str        # UUID for retrieval in /vs/select
    model: str                  # which LLM generated this
    phase: str                  # phase key used
    created_at: datetime

    def validate(self) -> bool:
        """Probabilities sum to 1.0 +/- 1e-6, all non-negative, sorted descending."""

    def argmax(self) -> Item:
        """Return highest-probability item."""

    def sample(self) -> Item:
        """Weighted random sample from distribution."""

    def filter_reweight(self, predicate: Callable[[Item], bool]) -> 'DiscreteDist':
        """Filter items by predicate, renormalize remaining probabilities."""
```

### 5.2 `repair_weight()`

Handles malformed LLM outputs — the most defensive function in the system:

- Converts percentage strings ("45%") to floats (0.45)
- Clamps negative values to 0.0
- Replaces NaN/Inf with 0.0 (postprocess_responses normalizes survivors later)
- Handles string values that look numeric ("0.3" as string)
- Falls back to uniform distribution if nothing is salvageable

### 5.3 `postprocess_responses()`

Takes raw LLM JSON output and produces a validated `DiscreteDist`:

1. Parse JSON from LLM response (handle markdown code fences, trailing commas)
2. Extract items and raw weights
3. Apply `repair_weight()` to each
4. Normalize so probabilities sum to 1.0
5. **Floor filter:** remove items with probability < `min_probability` (matches CHATS-lab `tau` parameter). If filtering would remove too many items, relax: keep top `min_k_survivors` regardless (default: `k - 2`, minimum 2). Log `tau_relaxed: true` when this happens.
6. Renormalize survivors so probabilities sum to 1.0
7. Sort descending by probability
8. Validate invariants (sum ≈ 1.0, all non-negative)
9. Assign `distribution_id` (UUID)
10. Return `DiscreteDist` with metadata including `tau_relaxed`, `num_filtered`

## 6. API Endpoints

### 6.1 `POST /vs/generate`

Generate k diverse responses with probability distribution.

**Request:**

```json
{
  "prompt": "Generate 5 different approaches to gap analysis for NSCLC immunotherapy CME",
  "system_prompt": "You are a medical education expert...",
  "model": "qwen3:14b",
  "k": 5,
  "tau": 0.08,
  "min_probability": 0.03,
  "phase": "gap_analysis",
  "confidence_framing": "confidence",
  "variant": "standard",
  "temperature": 1.0
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prompt` | string | required | The generation prompt |
| `system_prompt` | string | optional | System prompt prepended to VS instructions |
| `model` | string | phase default | Model identifier (e.g., `qwen3:14b`, `claude-sonnet-4-20250514`, `gpt-4o`) |
| `k` | int | phase default | Number of responses to generate |
| `tau` | float | phase default | Soft prompt ceiling — LLM is nudged to keep each response's confidence near this value (≈ 1/k) |
| `min_probability` | float | phase default | Postprocessing floor — responses with probability below this are filtered out (CHATS-lab's `tau` parameter) |
| `min_k_survivors` | int | `k - 2` (min 2) | If floor filtering would remove too many items, keep this many regardless |
| `phase` | string | `"custom"` | Phase key for defaults lookup |
| `confidence_framing` | string | `"confidence"` | How to frame probabilities to the LLM |
| `variant` | string | `"standard"` | VS variant: `standard`, `cot` (chain-of-thought), `multi` (multi-turn) |
| `temperature` | float | `1.0` | LLM sampling temperature |

**Response:**

```json
{
  "distribution_id": "a1b2c3d4-...",
  "model": "qwen3:14b",
  "phase": "gap_analysis",
  "k": 5,
  "tau": 0.08,
  "items": [
    {
      "content": "Focus on PD-L1 testing gaps across community oncology...",
      "probability": 0.09,
      "metadata": {
        "label": "conventional",
        "quality_score": null
      }
    },
    {
      "content": "Examine disparities in immunotherapy access for rural patients...",
      "probability": 0.08,
      "metadata": {
        "label": "novel",
        "quality_score": null
      }
    }
  ],
  "sum_probability": 1.0,
  "tau_relaxed": false,
  "num_filtered": 0,
  "created_at": "2026-03-14T12:00:00Z"
}
```

### 6.2 `POST /vs/select`

Select an item from a previously generated distribution.

**Request:**

```json
{
  "distribution_id": "a1b2c3d4-...",
  "strategy": "argmax"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `distribution_id` | string | required | ID from a prior `/vs/generate` response |
| `strategy` | string | `"argmax"` | Selection strategy: `argmax`, `sample`, `human` |
| `human_selection_index` | int | optional | Required when strategy is `human` — index of chosen item |

**Response:**

```json
{
  "selected": {
    "content": "Focus on PD-L1 testing gaps across community oncology...",
    "probability": 0.09,
    "metadata": {
      "label": "conventional",
      "quality_score": null
    }
  },
  "strategy_used": "argmax",
  "distribution_id": "a1b2c3d4-..."
}
```

### 6.3 `GET /health`

```json
{
  "status": "healthy",
  "ollama": "connected",
  "anthropic": "configured",
  "distributions_cached": 12
}
```

### 6.4 `GET /metrics`

Prometheus-format metrics:

```
# HELP vs_generations_total Total VS generation requests
# TYPE vs_generations_total counter
vs_generations_total{phase="gap_analysis",model="qwen3:14b"} 42

# HELP vs_generation_duration_seconds Time to generate distribution
# TYPE vs_generation_duration_seconds histogram
vs_generation_duration_seconds_bucket{le="5.0"} 38

# HELP vs_repair_weight_total Times repair_weight was invoked (malformed output)
# TYPE vs_repair_weight_total counter
vs_repair_weight_total{model="qwen3:14b"} 3

# HELP vs_selections_total Selection requests by strategy
# TYPE vs_selections_total counter
vs_selections_total{strategy="argmax"} 30
vs_selections_total{strategy="sample"} 8
vs_selections_total{strategy="human"} 4

# HELP vs_tau_relaxed_total Times min_probability floor was relaxed (not enough survivors)
# TYPE vs_tau_relaxed_total counter
vs_tau_relaxed_total{phase="gap_analysis"} 1

# HELP vs_items_filtered_total Items removed by min_probability floor
# TYPE vs_items_filtered_total counter
vs_items_filtered_total{phase="brainstorm"} 7

# HELP vs_distributions_cached Currently cached distributions
# TYPE vs_distributions_cached gauge
vs_distributions_cached 12
```

## 7. VS Prompt Construction

The service constructs a prompt that wraps the caller's prompt with VS instructions. The format instructs the LLM to:

1. Generate exactly k distinct responses
2. Assign each a probability (framed as "confidence") that must be below tau
3. Return structured JSON with content and probability fields

### 7.1 Template (Standard Variant)

```
You are asked to provide {k} distinct responses to the following prompt.
Each response should represent a genuinely different approach or perspective.

IMPORTANT: Assign a {confidence_framing} value to each response, representing
how likely you believe it is to be the best answer. Distribute your
{confidence_framing} as uniformly as possible — aim for each value to be
near {tau} (approximately 1/{k}). Avoid concentrating {confidence_framing}
on any single response. The values must sum to 1.0.

Respond in this exact JSON format:
{
  "responses": [
    {"content": "...", "confidence": 0.XX},
    ...
  ]
}

--- PROMPT ---
{prompt}
```

**Two-parameter design (matching CHATS-lab):**

The system uses two separate parameters for diversity control, corresponding to CHATS-lab's `probability_tuning` and `tau`:

| DHG Parameter | CHATS-lab Equivalent | Where It Acts | What It Does |
|---------------|---------------------|---------------|-------------|
| `tau` | `probability_tuning` | **Prompt** (soft ceiling) | Nudges the LLM toward uniform distribution — "aim for each value near {tau}". Not a hard gate; the LLM may deviate. |
| `min_probability` | `tau` | **Postprocessing** (hard floor) | Filters out responses the LLM self-rated as junk (probability < min_probability). Survivors are renormalized to sum to 1.0. |

**Why two parameters?** They solve different problems. `tau` in the prompt encourages the LLM to *generate* diverse outputs rather than concentrating all confidence on one. `min_probability` in postprocessing *removes* outputs the LLM itself flagged as low-quality — a garbage-collection step. CHATS-lab defaults to `probability_tuning=-1` (disabled) and `tau=0.12`. DHG enables both: tau=0.08 in prompt, min_probability=0.03 in postprocessing.

**Safety net:** If `min_probability` filtering would reduce survivors below `min_k_survivors`, the floor relaxes — top `min_k_survivors` items are kept regardless of probability (CHATS-lab's `tau_relaxed` mechanism). This prevents the system from filtering everything out when the LLM assigns very uniform probabilities.

### 7.2 Variants

| Variant | Behavior |
|---------|----------|
| `standard` | Single-shot generation, all k responses at once |
| `cot` | Chain-of-thought: LLM reasons about each response before assigning probability |
| `multi` | Multi-turn: generate one response at a time across k turns, with running distribution context |

v1 ships `standard` only. `cot` and `multi` are future additions — the prompt template and API field are designed to accommodate them.

## 8. LLM Router

### 8.1 Model Resolution

The `model` field in requests determines routing:

| Model Pattern | Route | Client |
|---------------|-------|--------|
| `qwen3:*`, `llama3*`, `nomic-*`, any Ollama tag | Ollama | `httpx` → `http://dhg-ollama:11434/api/generate` |
| `claude-*` | Anthropic | `anthropic` SDK → `api.anthropic.com` |
| `gpt-*`, `o1-*` | OpenAI-compatible | `openai` SDK → configurable base URL |

### 8.2 Phase Default Models

Each phase has a default model, overridable per request:

| Phase | Default Model | Rationale |
|-------|--------------|-----------|
| `brainstorm` | `qwen3:14b` | Local, fast, good for creative divergence |
| `cme_content` | `claude-sonnet-4-20250514` | High-stakes CME content needs top quality |
| `review` | `qwen3:14b` | Internal review, local-first |
| `human_review` | `claude-sonnet-4-20250514` | Human-facing output needs polish |
| `gap_analysis` | `qwen3:14b` | Enumeration task, local handles well |
| `custom` | `qwen3:14b` | Sensible default |

### 8.3 Connection Management

- Ollama: connection verified on startup via health check to `:11434/api/tags`
- Anthropic: API key presence checked on startup, actual auth verified on first call
- OpenAI-compatible: optional, configured via `OPENAI_API_BASE` and `OPENAI_API_KEY` env vars
- All connections report status via `/health` endpoint

### 8.4 Expected Latency

| Model | k | Typical Duration |
|-------|:-:|-----------------|
| `qwen3:14b` (Ollama, RTX 5080) | 5 | 30–60s |
| `qwen3:14b` (Ollama, RTX 5080) | 3 | 15–30s |
| `claude-sonnet-4-20250514` (API) | 5 | 10–20s |
| `claude-sonnet-4-20250514` (API) | 3 | 5–15s |

Server-side timeout: **120 seconds** per `/vs/generate` request. Callers should set matching or longer client timeouts.

## 9. Phase Defaults

| Phase Key | Default k | Default tau | Default min_p | Default Model | Use Case |
|-----------|:---------:|:-----------:|:------------:|---------------|----------|
| `brainstorm` | 5 | 0.08 | 0.03 | `qwen3:14b` | /ship Phase 1, agent ideation |
| `cme_content` | 5 | 0.08 | 0.03 | `claude-sonnet-4-20250514` | Needs assessment, curriculum, grant writing |
| `review` | 5 | 0.08 | 0.03 | `qwen3:14b` | Prose quality, compliance critique |
| `human_review` | 3 | 0.08 | 0.05 | `claude-sonnet-4-20250514` | Final options presented to humans (higher floor = stricter quality) |
| `gap_analysis` | 4 | 0.10 | 0.03 | `qwen3:14b` | Gap enumeration (slightly looser tau — gaps are more constrained) |
| `custom` | 5 | 0.08 | 0.03 | `qwen3:14b` | Default for unrecognized phases |

## 10. Phase Type Framework

VS applies differently depending on where a task falls in the divergent-convergent cycle:

| Phase Type | VS Behavior | Example |
|------------|------------|---------|
| **Diverge** | k=5, tau<0.10, tail sampling | Brainstorming, gap enumeration, marketing channels, curriculum approaches |
| **Evaluate** | k=5, tau<0.10, diverse critiques | Quality review, compliance check, failure scenario analysis |
| **Converge** | `argmax()` or human selection | Choosing final approach, approving plans, selecting outputs |
| **Execute** | No VS — deterministic | Code generation, SQL, Docker configs, file writes |

## 11. Human Review UX

### 11.1 Flow

1. VS generates k=5 options (diverge phase)
2. Quality gate filters to top 3 (by quality_score or probability)
3. Frontend receives 3 items with probabilities and labels
4. **Auto-select:** one item is pre-selected via VS probability-weighted sampling
5. **"Show alternatives"** button expands to reveal all 3 as unordered cards
6. Cards display: content preview, confidence badge, label (conventional/novel/exploratory)
7. User either accepts the auto-selection or picks an alternative
8. Selection is sent back via `POST /vs/select` with `strategy: "human"`

### 11.2 Center-Stage Bias Mitigation

- Cards are **unordered** — no numbering, no positional hierarchy
- Cards are rendered in **randomized order** on each view
- Labels use descriptive terms (conventional/novel/exploratory), not quality judgments
- The auto-selected option is marked but not visually dominant
- Confidence badges show the VS probability as a percentage

### 11.3 Confidence Badges

| Probability Range | Badge | Color |
|-------------------|-------|-------|
| 0.07 - 0.10 | Conventional | DHG Purple (#663399) |
| 0.04 - 0.069 | Novel | DHG Orange (#F77E2D) |
| < 0.04 | Exploratory | DHG Graphite (#32374A) |

Badge thresholds are relative to tau. These defaults assume tau=0.08; the service includes the computed label in item metadata.

## 12. Distribution Caching

Generated distributions are cached in-memory (TTL: 1 hour, max: 1000 entries) so that `/vs/select` can retrieve them by `distribution_id`. This avoids requiring the caller to store and re-send the full distribution.

- Cache is a simple dict with TTL eviction
- Cache miss on `/vs/select` returns 404 with a clear message
- `/health` reports `distributions_cached` count
- `/metrics` exposes cache hit/miss counters
- No persistence — distributions are ephemeral by design. Cache is lost on container restart.
- **Callers MUST store the full `/vs/generate` response** if they need the distribution beyond the cache window (e.g., human review that may take hours). The `/vs/select` endpoint is a convenience for quick automated flows, not a durable store.

## 13. Error Handling

| Scenario | Behavior |
|----------|----------|
| LLM returns unparseable JSON | Retry once with a "please return valid JSON" follow-up prompt. If still unparseable, return 502 with raw output in error detail. |
| LLM returns k-1 or k+1 items | Accept if within ±1 of requested k. Renormalize probabilities. Log a warning. |
| Probabilities don't sum to 1.0 | `repair_weight()` renormalizes. Always succeeds — never fails on probability math. |
| Ollama unreachable | Return 503 with `{"error": "ollama_unavailable", "detail": "..."}`. Health endpoint reflects status. |
| Anthropic API error | Return 502 with upstream error detail. Respect rate limits. |
| Distribution ID not found | Return 404: `{"error": "distribution_not_found", "detail": "Distribution expired or never existed"}` |
| Unsupported variant requested | Return 422: `{"error": "unsupported_variant", "detail": "Only 'standard' is supported in v1"}` |
| `human_selection_index` out of bounds | Return 422: `{"error": "invalid_index", "detail": "Index must be >= 0 and < number of items"}` |
| Evaluation with < 2 items | Return 422: `{"error": "insufficient_items", "detail": "Evaluation requires at least 2 items"}` |
| TTCT judge model unavailable (TTCT-only request) | Return 503: `{"error": "ttct_unavailable", "detail": "..."}` |
| TTCT judge model unavailable (mixed request) | Return 200 with `diversity` results and `ttct: {"error": "..."}` — partial success |

## 14. Integration Points

### 14.1 LangGraph Agents (Agent-Level VS)

Each of the 11 content agents can call `/vs/generate` during their diverge phase. Example integration in a LangGraph node:

```python
# Inside a LangGraph agent node
VS_ENGINE_URL = os.getenv("VS_ENGINE_URL", "http://dhg-vs-engine:8000")

async def generate_gap_analysis(state: GapAnalysisState) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{VS_ENGINE_URL}/vs/generate",
            json={
                "prompt": f"Generate gap analysis approaches for {state['disease_state']}",
                "phase": "gap_analysis",
                "model": state.get("model_override", None),
            },
            timeout=120.0,
        )
    dist = response.json()
    # Store full distribution in state (survives cache expiry)
    # Use argmax for automated selection, or pass to human review
    selected = dist["items"][0]  # argmax (highest probability)
    return {"gap_approaches": dist, "selected_approach": selected}
```

### 14.2 Orchestrator-Level VS

The orchestrator can use VS for routing decisions, quality gate strategies, and human review presentation:

- **Routing:** "Should this project use the fast pipeline or the thorough pipeline?" → VS generates k=3 routing strategies with probabilities
- **Quality gates:** "Generate 5 different critique perspectives for this needs assessment" → diverse evaluation
- **Human review:** Present the top 3 outputs to the human reviewer with confidence badges

### 14.3 `/ship` Workflow

- **Phase 1 (Brainstorm):** VS generates diverse feature approaches
- **Phase 6 (Review):** VS generates diverse critique perspectives for the code review

### 14.4 Frontend Inbox

The frontend renders VS distributions using the UX pattern from Section 11. The inbox component receives the `/vs/generate` response and:

1. Auto-selects one item (weighted sample)
2. Renders "Show alternatives" expander
3. On expand, renders unordered cards with confidence badges
4. On selection, calls `/vs/select` with `strategy: "human"`

## 15. Prometheus Scrape Configuration

Add to the existing Prometheus config:

```yaml
- job_name: 'vs-engine'
  static_configs:
    - targets: ['dhg-vs-engine:8000']
  metrics_path: /metrics
  scrape_interval: 15s
```

## 16. Implementation Sequence

### Phase 1: Core Service

- `services/vs-engine/` directory structure
- `distribution.py` — port Item, DiscreteDist, repair_weight, postprocess_responses from CHATS-lab
- `prompt_builder.py` — VS prompt construction (standard variant)
- `selection.py` — argmax, sample, filter_reweight
- `config.py` — phase defaults, env var loading
- Unit tests for all core math
- Dockerfile

### Phase 2: API + LLM Router

- `main.py` — FastAPI app with `/vs/generate`, `/vs/select`, `/health`, `/metrics`
- `llm_router.py` — Ollama and Anthropic clients
- Distribution caching (in-memory, TTL)
- Integration tests against Ollama
- Docker Compose entry in `docker-compose.override.yml`
- Prometheus scrape config

### Phase 3: LangGraph Agent Integration

- Wire VS into 1-2 pilot agents (gap analysis, needs assessment)
- Validate round-trip: agent → VS → distribution → selection → agent state
- Performance benchmarks (latency overhead of VS vs. direct LLM call)

### Phase 4: /ship + Frontend Integration

- Wire VS into /ship Phase 1 (brainstorm) and Phase 6 (review)
- Frontend inbox component for VS distribution rendering
- Auto-select + "show alternatives" UX
- Confidence badges with DHG brand colors

## 17. Evaluation Framework

The VS engine includes an evaluation layer ported from CHATS-lab's analysis suite. This provides standardized, academically-grounded benchmarks for measuring whether VS is working — producing genuinely diverse, high-quality outputs rather than paraphrased copies of the same answer.

### 17.1 Evaluators

Two evaluators are adopted for v1. Both are academically standard and map directly to DHG's CME use case.

#### DiversityEvaluator (from CHATS-lab `analysis/evals/diversity.py`)

**What it measures:** Pairwise cosine similarity between generated responses using text embeddings. The core question: "Are these k outputs actually different, or are they k rewrites of the same idea?"

**Academic basis:** Embedding-based diversity measurement is a well-established NLP evaluation technique used across dozens of papers on text generation evaluation.

**Metrics returned:**

| Metric | Type | Description |
|--------|------|-------------|
| `avg_diversity` | float | Mean pairwise cosine distance (0.0 = identical, 1.0 = orthogonal) |
| `min_diversity` | float | Closest pair — the worst-case diversity |
| `max_diversity` | float | Most different pair |
| `std_diversity` | float | Uniformity of diversity across pairs |
| `vocabulary_richness` | float | Unique words / total words across all responses |
| `avg_response_length` | int | Mean token count per response |

**Adaptation from CHATS-lab:** Original uses OpenAI `text-embedding-3-small`. DHG uses Ollama `nomic-embed-text` (768d, already deployed at `:11434`). The math (pairwise cosine similarity) is identical — only the embedding provider changes. ~20-line adapter.

**CME application:**
- "Generate 5 gap analyses" → diversity score validates they surface genuinely different educational gaps
- "Generate 5 cold opens for needs assessment" → diversity score proves different framing approaches
- Track avg_diversity over time as tau and min_probability are tuned — the optimization feedback loop

#### TTCTEvaluator (from CHATS-lab `analysis/evals/quality.py`)

**What it measures:** Torrance Tests of Creative Thinking — the most widely used creativity assessment framework in psychology and education research, established in the 1960s. Adapted here as an LLM-as-judge evaluation.

**Academic basis:** TTCT is *the* standard creativity assessment, used in 60+ years of educational research. The LLM-as-judge adaptation (using a model to score outputs on rubric-based dimensions) follows established LLM evaluation methodology.

**Dimensions (each scored 1-5):**

| Dimension | Weight | What It Measures | CME Relevance |
|-----------|:------:|-----------------|---------------|
| **Fluency** | 25% | Number of distinct ideas generated | How many educational needs/gaps were identified? |
| **Flexibility** | 25% | Variety of categories/approaches | Does the curriculum approach from multiple pedagogical angles? |
| **Originality** | 25% | Unusualness relative to typical responses | Does this proposal stand out from hundreds of similar submissions? |
| **Elaboration** | 25% | Depth and detail of development | Is the gap analysis supported with sufficient clinical evidence? |

**Composite score:** Weighted average of all four dimensions (1.0–5.0 scale).

**Adaptation from CHATS-lab:** Original uses GPT-4.1 as judge via structured output (Pydantic models). DHG uses Claude Sonnet as judge — consistent with the production agent LLM and avoids introducing a new provider dependency. For cost-free local evaluation during development, Ollama `qwen3:14b` can serve as a lower-fidelity judge.

**CME application:**
- Score every VS-generated output on all four dimensions
- **Killer metric:** Compare TTCT scores *with* VS vs. *without* VS (single-response baseline) — quantified proof that VS adds value
- Use TTCT composite score as a quality gate input in the orchestrator
- Track TTCT scores by agent to identify which agents benefit most from VS

#### CreativityIndexEvaluator (Deferred)

Measures overlap between generated text and LLM pretraining data via the Infini-gram API (CMU). Deferred to a future version because: (a) depends on an external API that could change, (b) requires LLaMA tokenizer — a dependency DHG doesn't otherwise need, (c) in CME, you *want* overlap with established medical literature — a gap analysis that's 95% "creative" probably means it's hallucinating. Revisit once Diversity and TTCT baselines are established.

### 17.2 Evaluation API

#### `POST /vs/evaluate`

Evaluate a set of generated responses for diversity and quality.

**Request:**

```json
{
  "items": [
    {"content": "Focus on PD-L1 testing gaps...", "probability": 0.09},
    {"content": "Examine disparities in immunotherapy access...", "probability": 0.08}
  ],
  "evaluators": ["diversity", "ttct"],
  "judge_model": "claude-sonnet-4-20250514",
  "embedding_model": "nomic-embed-text"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `items` | array | required | The generated responses to evaluate (from `/vs/generate` response) |
| `evaluators` | array | `["diversity"]` | Which evaluators to run: `diversity`, `ttct`, or both |
| `judge_model` | string | `claude-sonnet-4-20250514` | Model for TTCT scoring (LLM-as-judge) |
| `embedding_model` | string | `nomic-embed-text` | Model for diversity embeddings (via Ollama) |

**Response:**

```json
{
  "diversity": {
    "avg_diversity": 0.72,
    "min_diversity": 0.58,
    "max_diversity": 0.89,
    "std_diversity": 0.11,
    "vocabulary_richness": 0.64,
    "avg_response_length": 312
  },
  "ttct": {
    "fluency": 4.2,
    "flexibility": 3.8,
    "originality": 4.0,
    "elaboration": 3.5,
    "composite": 3.88,
    "per_item_scores": [
      {
        "item_index": 0,
        "fluency": 4, "flexibility": 4, "originality": 3, "elaboration": 4,
        "composite": 3.75,
        "justification": "Comprehensive PD-L1 gap analysis with strong clinical evidence..."
      }
    ]
  },
  "evaluated_at": "2026-03-14T12:00:00Z"
}
```

### 17.3 Prometheus Metrics for Evaluation

```
# HELP vs_diversity_score Distribution of avg_diversity scores
# TYPE vs_diversity_score histogram
vs_diversity_score_bucket{phase="gap_analysis",le="0.5"} 2
vs_diversity_score_bucket{phase="gap_analysis",le="0.7"} 15
vs_diversity_score_bucket{phase="gap_analysis",le="0.9"} 38

# HELP vs_ttct_composite Distribution of TTCT composite scores
# TYPE vs_ttct_composite histogram
vs_ttct_composite_bucket{phase="cme_content",le="3.0"} 5
vs_ttct_composite_bucket{phase="cme_content",le="4.0"} 22
vs_ttct_composite_bucket{phase="cme_content",le="5.0"} 35
```

These feed directly into Grafana dashboards: diversity trends over time, TTCT score distributions by phase, and the VS-vs-baseline comparison panel.

### 17.4 Implementation Scope

The evaluation layer adds to the file layout:

```
services/vs-engine/
├── ...existing files...
├── evaluators/
│   ├── __init__.py
│   ├── diversity.py          # DiversityEvaluator (Ollama nomic-embed-text)
│   └── ttct.py               # TTCTEvaluator (Claude/Ollama LLM-as-judge)
└── tests/
    ├── ...existing tests...
    ├── test_diversity.py     # Known-similar and known-different response pairs
    └── test_ttct.py          # Score consistency and rubric adherence
```

Ported from CHATS-lab `analysis/evals/diversity.py` (~150 lines) and `analysis/evals/quality.py` (~200 lines). Retains Apache 2.0 license headers. Total ported code expands from ~300 lines to ~650 lines.

### 17.5 Integration with Implementation Sequence

Add as Phase 5 (after Phase 4: /ship + Frontend Integration):

**Phase 5: Evaluation Layer**
- Port DiversityEvaluator with Ollama nomic-embed-text adapter
- Port TTCTEvaluator with Claude Sonnet judge adapter
- `/vs/evaluate` endpoint
- Evaluation Prometheus metrics
- Grafana dashboard panels (diversity trends, TTCT distributions, VS-vs-baseline)
- Integration tests: known-similar pairs score low diversity, known-different pairs score high

## 18. Testing Strategy

| Level | Scope | What |
|-------|-------|------|
| Unit | `distribution.py` | repair_weight with malformed inputs (percentages, negatives, NaN, strings), DiscreteDist validation, normalization edge cases |
| Unit | `prompt_builder.py` | Prompt template rendering for all phases, tau injection, framing substitution |
| Unit | `selection.py` | argmax determinism, sample distribution over many runs, filter_reweight renormalization |
| Integration | `/vs/generate` | Round-trip with Ollama (qwen3:14b), verify DiscreteDist shape and invariants |
| Integration | `/vs/select` | Cache hit/miss, all three strategies, expired distribution handling |
| Integration | `/health` | Ollama up/down, Anthropic configured/unconfigured |
| Unit | `evaluators/diversity.py` | Known-identical responses → diversity ≈ 0.0, known-different → diversity > 0.5, vocabulary richness calculation |
| Unit | `evaluators/ttct.py` | Score parsing, rubric consistency, composite calculation, judge prompt construction |
| Integration | `/vs/evaluate` | Diversity with Ollama embeddings, TTCT with judge model, both-evaluators request, partial failure (TTCT unavailable) |
| Smoke | Docker | Container builds, starts, responds to /health within 30s |

## 19. Attribution

Core distribution math ported from:

- **Project:** Verbalized Sampling (CHATS-lab)
- **Authors:** Northeastern University, Stanford University, West Virginia University
- **Paper:** arXiv 2510.01171
- **Repository:** https://github.com/CHATS-lab/verbalized-sampling
- **License:** Apache 2.0
- **Website:** https://www.verbalized-sampling.com/

All ported files include Apache 2.0 license headers and credit the original authors. The DHG VS Engine is a derivative work that ports core math (~300 lines from `selection.py`) and evaluation framework (~350 lines from `analysis/evals/diversity.py` and `analysis/evals/quality.py`), and implements its own LLM routing, API layer, evaluation adapters, and Docker service architecture.

---

*Spec written 2026-03-14. Pending spec review loop and Stephen approval.*
