# services/vs-engine/main.py
"""VS Engine — FastAPI application.

Endpoints:
  GET  /health        — Component health check
  GET  /metrics       — Prometheus metrics (text/plain)
  POST /vs/generate   — Generate a verbalized sampling distribution
  POST /vs/select     — Select one item from a cached distribution
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from pydantic import BaseModel, Field, field_validator

import llm_router
from config import get_ollama_url, get_phase_defaults, get_log_level
from distribution import DiscreteDist, Item, postprocess_responses
from prompt_builder import build_vs_prompt
from selection import select_from_distribution

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=get_log_level(),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("vs-engine")

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

GENERATIONS_TOTAL = Counter(
    "vs_generations_total",
    "Total number of VS generation requests",
    ["phase", "model", "status"],
)
GENERATION_DURATION = Histogram(
    "vs_generation_duration_seconds",
    "Latency of /vs/generate LLM call in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)
REPAIR_WEIGHT_TOTAL = Counter(
    "vs_repair_weight_total",
    "Total weight repair operations applied",
)
SELECTIONS_TOTAL = Counter(
    "vs_selections_total",
    "Total number of VS selection requests",
    ["strategy"],
)
TAU_RELAXED_TOTAL = Counter(
    "vs_tau_relaxed_total",
    "Number of times tau relaxation was applied",
)
ITEMS_FILTERED_TOTAL = Counter(
    "vs_items_filtered_total",
    "Total number of items filtered by min_probability",
)
DISTRIBUTIONS_CACHED = Gauge(
    "vs_distributions_cached",
    "Current number of distributions held in the in-memory cache",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_VARIANTS = {"standard"}

# Label thresholds
LABEL_CONVENTIONAL = 0.07
LABEL_NOVEL = 0.04
# anything below LABEL_NOVEL → "exploratory"

# Cache settings
CACHE_TTL_SECONDS = 3600
CACHE_MAX_ENTRIES = 1000

# JSON parse retry limit
MAX_PARSE_RETRIES = 3

# ---------------------------------------------------------------------------
# In-memory distribution cache
# ---------------------------------------------------------------------------

_cache: Dict[str, Dict[str, Any]] = {}
# Structure: { distribution_id: { "dist": DiscreteDist, "created_at": float, "model": str, "phase": str } }


def _evict_expired() -> None:
    """Remove entries older than CACHE_TTL_SECONDS."""
    now = time.time()
    expired = [k for k, v in _cache.items() if now - v["created_at"] > CACHE_TTL_SECONDS]
    for k in expired:
        del _cache[k]
    DISTRIBUTIONS_CACHED.set(len(_cache))


def _cache_store(dist: DiscreteDist, model: str, phase: str) -> str:
    """Insert a distribution into the cache, evict if over max size. Returns new ID."""
    _evict_expired()
    # If still over limit, evict oldest entries
    while len(_cache) >= CACHE_MAX_ENTRIES:
        oldest_key = min(_cache, key=lambda k: _cache[k]["created_at"])
        del _cache[oldest_key]

    dist_id = str(uuid.uuid4())
    _cache[dist_id] = {
        "dist": dist,
        "created_at": time.time(),
        "model": model,
        "phase": phase,
    }
    DISTRIBUTIONS_CACHED.set(len(_cache))
    return dist_id


def _cache_get(dist_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a cache entry or None if missing/expired."""
    _evict_expired()
    return _cache.get(dist_id)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    prompt: str  # Required — no default
    k: int = Field(default=5, ge=1, le=20, description="Number of candidate responses")
    tau: float = Field(default=0.08, gt=0.0, lt=1.0, description="Uniform target per response")
    phase: Optional[str] = Field(default=None, description="Phase name to load defaults from")
    model: Optional[str] = Field(default=None, description="Override model name")
    variant: str = Field(default="standard", description="Generation variant")
    min_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, v: str) -> str:
        if v not in SUPPORTED_VARIANTS:
            raise ValueError(f"variant must be one of {SUPPORTED_VARIANTS}, got {v!r}")
        return v


class SelectRequest(BaseModel):
    distribution_id: str
    strategy: str = Field(default="argmax", description="One of: argmax, sample, human")
    human_selection_index: Optional[int] = Field(default=None, ge=0)


class ItemResponse(BaseModel):
    content: str
    probability: float
    label: str  # "conventional", "novel", or "exploratory"


class GenerateResponse(BaseModel):
    distribution_id: str
    items: List[ItemResponse]
    phase: Optional[str]
    model: str
    tau_relaxed: bool
    repairs_applied: int


class SelectResponse(BaseModel):
    distribution_id: str
    strategy_used: str
    selected: ItemResponse

# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)

_CONTENT_KEYS = ("content", "text", "response")
_CONFIDENCE_KEYS = ("confidence", "probability", "likelihood")


def _parse_llm_json(raw: str) -> List[Dict[str, Any]]:
    """Parse LLM output into a list of response dicts.

    Handles:
    - Markdown code fences (```json ... ```)
    - Multiple key names for content (content/text/response)
    - Multiple key names for weight (confidence/probability/likelihood)

    Returns:
        List of dicts with keys "content" (str) and "confidence" (float/str).

    Raises:
        ValueError: If JSON cannot be parsed or "responses" key is missing.
    """
    text = raw.strip()

    # Strip markdown fences if present
    fence_match = _FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object at top level")

    responses = data.get("responses")
    if not isinstance(responses, list):
        raise ValueError("Missing or non-list 'responses' key in JSON")

    normalized: List[Dict[str, Any]] = []
    for entry in responses:
        # Extract content
        content = ""
        for ck in _CONTENT_KEYS:
            if ck in entry:
                content = str(entry[ck])
                break

        # Extract weight
        weight = 0.0
        for wk in _CONFIDENCE_KEYS:
            if wk in entry:
                weight = entry[wk]
                break

        normalized.append({"content": content, "confidence": weight})

    return normalized


def _assign_label(probability: float) -> str:
    if probability >= LABEL_CONVENTIONAL:
        return "conventional"
    if probability >= LABEL_NOVEL:
        return "novel"
    return "exploratory"

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VS Engine",
    description="Verbalized Sampling microservice for DHG AI Factory",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Return component health status."""
    ollama_url = get_ollama_url()
    ollama_status = await llm_router.check_ollama_health(ollama_url)
    anthropic_status = llm_router.check_anthropic_configured()
    _evict_expired()
    return {
        "status": "healthy",
        "ollama": ollama_status,
        "anthropic": anthropic_status,
        "distributions_cached": len(_cache),
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    """Expose Prometheus metrics in text format."""
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/vs/generate", response_model=GenerateResponse)
async def generate_distribution(request: GenerateRequest) -> GenerateResponse:
    """Generate a verbalized sampling distribution.

    Applies phase defaults when `phase` is provided, then any explicit overrides.
    Caches the resulting DiscreteDist for retrieval by /vs/select.
    """
    # Resolve effective settings
    if request.phase:
        defaults = get_phase_defaults(request.phase)
    else:
        defaults = get_phase_defaults("custom")

    effective_k = request.k if request.k != 5 else defaults.get("k", request.k)
    # If k was explicitly provided (not default), use it; otherwise fall through to phase default.
    # Pydantic default for k is 5, so distinguish phase-driven k from explicit.
    # Simplest correct approach: always prefer explicit fields that differ from pydantic default.
    # But since we can't tell 5 from "not provided", use phase default only for fields not set.
    # The spec says phase defaults; explicit fields override. Use explicit if provided.
    # We re-read from the raw request body — since Pydantic filled defaults, just use them.
    # Strategy: phase defaults fill in blanks; explicit request fields always win.
    effective_k = request.k  # request.k always has a value (defaulted by Pydantic)
    effective_tau = request.tau
    effective_model = request.model or defaults.get("model", "qwen3:14b")
    effective_min_probability = request.min_probability
    if effective_min_probability is None:
        effective_min_probability = defaults.get("min_probability", 0.03)
    effective_phase = request.phase or "custom"

    # Build VS prompt
    vs_prompt = build_vs_prompt(
        user_prompt=request.prompt,
        k=effective_k,
        tau=effective_tau,
        confidence_framing=defaults.get("confidence_framing", "confidence"),
    )

    ollama_url = get_ollama_url()

    # LLM call with retry on unparseable JSON
    parsed_responses: List[Dict[str, Any]] = []
    last_error: Optional[Exception] = None
    call_count = 0

    for attempt in range(MAX_PARSE_RETRIES):
        call_count += 1
        t0 = time.time()
        try:
            raw_output = await llm_router.generate(
                prompt=vs_prompt,
                model=effective_model,
                ollama_url=ollama_url,
            )
        except httpx.ConnectError as exc:
            GENERATIONS_TOTAL.labels(
                phase=effective_phase, model=effective_model, status="503"
            ).inc()
            raise HTTPException(
                status_code=503,
                detail=f"LLM provider unreachable: {exc}",
            ) from exc
        except httpx.TimeoutException as exc:
            GENERATIONS_TOTAL.labels(
                phase=effective_phase, model=effective_model, status="503"
            ).inc()
            raise HTTPException(
                status_code=503,
                detail=f"LLM provider timed out: {exc}",
            ) from exc
        except Exception as exc:
            GENERATIONS_TOTAL.labels(
                phase=effective_phase, model=effective_model, status="502"
            ).inc()
            raise HTTPException(
                status_code=502,
                detail=f"LLM generation error: {exc}",
            ) from exc
        finally:
            elapsed = time.time() - t0
            GENERATION_DURATION.observe(elapsed)

        # Try to parse
        try:
            parsed_responses = _parse_llm_json(raw_output)
            last_error = None
            break
        except ValueError as exc:
            last_error = exc
            logger.warning(
                "JSON parse failure on attempt %d/%d: %s", attempt + 1, MAX_PARSE_RETRIES, exc
            )
            # Continue to retry

    if last_error is not None:
        # All retries exhausted
        GENERATIONS_TOTAL.labels(
            phase=effective_phase, model=effective_model, status="502"
        ).inc()
        raise HTTPException(
            status_code=502,
            detail=f"LLM returned unparseable JSON after {MAX_PARSE_RETRIES} attempts: {last_error}",
        )

    # Postprocess into distribution
    # postprocess_responses expects dicts with "response" and weight_mode key
    # Our _parse_llm_json normalizes to "content" + "confidence".
    # Adapt to what postprocess_responses expects.
    adapted = [
        {"response": r["content"], "confidence": r["confidence"]}
        for r in parsed_responses
    ]

    min_k_survivors = max(1, effective_k // 2) if effective_k > 1 else 1
    items, trace = postprocess_responses(
        parsed_responses=adapted,
        min_probability=effective_min_probability,
        min_k_survivors=min_k_survivors,
        weight_mode="confidence",
    )

    # Track metrics
    repairs_count = sum(len(r.get("tags", [])) for r in trace.get("repairs", []))
    if repairs_count:
        REPAIR_WEIGHT_TOTAL.inc(repairs_count)
    if trace.get("tau_relaxed"):
        TAU_RELAXED_TOTAL.inc()
    n_filtered = trace.get("n_zero_filtered", 0)
    if n_filtered:
        ITEMS_FILTERED_TOTAL.inc(n_filtered)

    # Build DiscreteDist (items are already sorted + normalized by postprocess_responses)
    dist = DiscreteDist(items=items, trace=trace)

    # Cache it
    dist_id = _cache_store(dist, effective_model, effective_phase)

    GENERATIONS_TOTAL.labels(
        phase=effective_phase, model=effective_model, status="200"
    ).inc()

    # Build response items
    item_responses = [
        ItemResponse(
            content=item.text,
            probability=item.p,
            label=_assign_label(item.p),
        )
        for item in dist
    ]

    return GenerateResponse(
        distribution_id=dist_id,
        items=item_responses,
        phase=request.phase,
        model=effective_model,
        tau_relaxed=bool(trace.get("tau_relaxed", False)),
        repairs_applied=repairs_count,
    )


@app.post("/vs/select", response_model=SelectResponse)
async def select_item(request: SelectRequest) -> SelectResponse:
    """Select one item from a cached distribution.

    Raises 404 if the distribution_id is not found in cache.
    Raises 422 if strategy is 'human' and human_selection_index is missing or out of range.
    """
    entry = _cache_get(request.distribution_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Distribution '{request.distribution_id}' not found in cache. "
                   "It may have expired or never existed.",
        )

    dist: DiscreteDist = entry["dist"]

    # Validate human strategy requirements before calling select_from_distribution
    if request.strategy == "human":
        if request.human_selection_index is None:
            raise HTTPException(
                status_code=422,
                detail="human_selection_index is required when strategy is 'human'",
            )
        if request.human_selection_index >= len(dist):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"human_selection_index {request.human_selection_index} is out of range "
                    f"for distribution with {len(dist)} items"
                ),
            )

    try:
        selected_item = select_from_distribution(
            dist=dist,
            strategy=request.strategy,
            human_selection_index=request.human_selection_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    SELECTIONS_TOTAL.labels(strategy=request.strategy).inc()

    return SelectResponse(
        distribution_id=request.distribution_id,
        strategy_used=request.strategy,
        selected=ItemResponse(
            content=selected_item.text,
            probability=selected_item.p,
            label=_assign_label(selected_item.p),
        ),
    )
