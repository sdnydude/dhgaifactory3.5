# Intake Prefill Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI-powered prefill agent that takes CME intake Section A inputs, researches the disease area via PubMed, and generates draft values for sections B through H — reducing manual form entry from 41 fields to review-and-accept.

**Architecture:** A new 4-node LangGraph agent (`intake_prefill`) that queries PubMed for literature context, then makes a single structured LLM call to generate section drafts. The registry API proxies requests to LangGraph Cloud, and the frontend adds a "Research & Prefill" button with accept/clear controls at bulk, per-section, and per-field granularity.

**Tech Stack:** LangGraph (StateGraph), PubMedClient (existing shared module), ChatAnthropic (Claude Sonnet), FastAPI + httpx (registry proxy), Next.js + Zustand + shadcn/ui (frontend)

**Design Spec:** `docs/superpowers/specs/2026-04-10-intake-prefill-agent-design.md`

**Spec Deviation:** The spec calls for creating `tools/pubmed.py` by extracting PubMedClient from research_agent.py. This is already done — `pubmed_client.py` exists as a standalone shared module. The new agent imports from it directly. No `tools/` directory needed.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py` | Create | 4-node agent: search_literature, build_context, generate_prefill, validate_output |
| `langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py` | Create | Unit tests for all 4 nodes + graph structure |
| `langgraph_workflows/dhg-agents-cloud/langgraph.json` | Modify | Register `intake_prefill` graph |
| `registry/cme_endpoints.py` | Modify | Add `POST /api/cme/intake/prefill` endpoint |
| `registry/test_cme_endpoints.py` | Modify | Add tests for prefill endpoint |
| `frontend/src/types/cme.ts` | Modify | Add `PrefillResponse` interface |
| `frontend/src/lib/registryApi.ts` | Modify | Add `prefillIntake()` function |
| `frontend/src/stores/intake-store.ts` | Modify | Add prefill state tracking + accept/clear actions |
| `frontend/src/components/intake/section-nav.tsx` | Modify | Add AI Draft indicators + per-section accept/clear |
| `frontend/src/components/intake/intake-form.tsx` | Modify | Add prefill button, loading state, accept/clear banner |

---

## Task 1: Agent State + Graph Skeleton

**Files:**
- Create: `langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py`
- Create: `langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py`

- [ ] **Step 1: Write the failing test for graph structure**

```python
# langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py
"""
Tests for the Intake Prefill Agent (intake_prefill_agent.py).

Covers:
- Graph construction and node inventory
- Individual node functions with mocked LLM
- Validation logic
- Error handling / fallback behaviour

Run with: pytest langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py -v
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import intake_prefill_agent as ipa


class TestGraphStructure:
    """Verify the compiled graph has the expected nodes and edges."""

    def test_graph_has_four_nodes(self):
        nodes = list(ipa.graph.nodes)
        expected = {"search_literature", "build_context", "generate_prefill", "validate_output"}
        # LangGraph adds __start__ and __end__ automatically
        agent_nodes = {n for n in nodes if not n.startswith("__")}
        assert agent_nodes == expected

    def test_graph_exports_as_graph(self):
        """The module-level `graph` is a compiled StateGraph."""
        assert hasattr(ipa, "graph")
        assert hasattr(ipa.graph, "invoke")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestGraphStructure -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'intake_prefill_agent'`

- [ ] **Step 3: Create the agent skeleton with state and empty graph**

```python
# langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py
"""
Intake Prefill Agent
====================
Takes Section A inputs from the CME intake form, researches the disease area
via PubMed, and generates draft values for sections B through H.

Graph: START -> search_literature -> build_context -> generate_prefill -> validate_output -> END
"""

import asyncio
import json
import logging
import os
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable

from pubmed_client import PubMedClient
from tracing import traced_node

logger = logging.getLogger(__name__)


# =============================================================================
# STATE
# =============================================================================

class IntakePrefillState(TypedDict):
    """State for the intake prefill agent."""
    # INPUT
    therapeutic_area: str
    disease_state: str
    target_audience_primary: list[str]
    target_hcp_types: list[str]
    project_name: str

    # PROCESSING
    messages: Annotated[list, add_messages]
    pubmed_results: list[dict]
    research_context: str

    # OUTPUT
    prefill_sections: dict
    research_summary: str
    confidence: dict

    # METADATA
    errors: list[dict]
    total_tokens: int
    total_cost: float


# =============================================================================
# LLM CLIENT
# =============================================================================

class LLMClient:
    """Claude-based LLM client with cost tracking."""

    def __init__(self):
        self.model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
        )
        self.cost_per_1k_input = 0.003
        self.cost_per_1k_output = 0.015

    @traceable(name="intake_prefill_llm_call", run_type="llm")
    async def generate(self, system: str, prompt: str) -> dict:
        """Generate response with cost tracking."""
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
        response = await self.model.ainvoke(messages)
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = response.usage_metadata.get("input_tokens", 0)
            output_tokens = response.usage_metadata.get("output_tokens", 0)
        cost = (input_tokens / 1000 * self.cost_per_1k_input) + \
               (output_tokens / 1000 * self.cost_per_1k_output)
        return {
            "content": response.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
        }


llm = LLMClient()


# =============================================================================
# NODE FUNCTIONS
# =============================================================================

@traceable(name="intake_prefill.search_literature", run_type="chain")
@traced_node("intake_prefill", "search_literature")
async def search_literature(state: IntakePrefillState) -> dict:
    """Search PubMed for literature relevant to the disease state."""
    raise NotImplementedError("Task 2")


@traceable(name="intake_prefill.build_context", run_type="chain")
@traced_node("intake_prefill", "build_context")
async def build_context(state: IntakePrefillState) -> dict:
    """Parse PubMed results into a structured research context string."""
    raise NotImplementedError("Task 3")


@traceable(name="intake_prefill.generate_prefill", run_type="chain")
@traced_node("intake_prefill", "generate_prefill")
async def generate_prefill(state: IntakePrefillState) -> dict:
    """Single LLM call to generate draft values for sections B-H."""
    raise NotImplementedError("Task 4")


@traceable(name="intake_prefill.validate_output", run_type="chain")
@traced_node("intake_prefill", "validate_output")
async def validate_output(state: IntakePrefillState) -> dict:
    """Type-check and sanitize the LLM output against section schemas."""
    raise NotImplementedError("Task 5")


# =============================================================================
# GRAPH
# =============================================================================

builder = StateGraph(IntakePrefillState)

builder.add_node("search_literature", search_literature)
builder.add_node("build_context", build_context)
builder.add_node("generate_prefill", generate_prefill)
builder.add_node("validate_output", validate_output)

builder.set_entry_point("search_literature")
builder.add_edge("search_literature", "build_context")
builder.add_edge("build_context", "generate_prefill")
builder.add_edge("generate_prefill", "validate_output")
builder.add_edge("validate_output", END)

graph = builder.compile()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestGraphStructure -v`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py
git commit -m "feat(intake-prefill): add agent skeleton with state, LLM client, and 4-node graph"
```

---

## Task 2: search_literature Node

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py`
- Modify: `langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py`

- [ ] **Step 1: Write the failing tests for search_literature**

Append to `tests/test_intake_prefill.py`:

```python
# ---------------------------------------------------------------------------
# search_literature node tests
# ---------------------------------------------------------------------------

def _make_sample_state(**overrides) -> dict:
    """Build a minimal IntakePrefillState dict for unit tests."""
    base = {
        "therapeutic_area": "cardiology",
        "disease_state": "heart failure with reduced ejection fraction",
        "target_audience_primary": ["cardiologists", "internists"],
        "target_hcp_types": ["MD/DO"],
        "project_name": "HFrEF GDMT Update 2026",
        "messages": [],
        "pubmed_results": [],
        "research_context": "",
        "prefill_sections": {},
        "research_summary": "",
        "confidence": {},
        "errors": [],
        "total_tokens": 0,
        "total_cost": 0.0,
    }
    base.update(overrides)
    return base


class TestSearchLiterature:
    """Tests for search_literature node."""

    @pytest.mark.asyncio
    async def test_returns_pubmed_results(self):
        """Successful PubMed search populates pubmed_results."""
        sample_articles = [
            {"pmid": "12345", "title": "HFrEF GDMT Review", "abstract": "...", "year": 2025},
            {"pmid": "67890", "title": "SGLT2i in Heart Failure", "abstract": "...", "year": 2024},
        ]
        mock_pubmed = MagicMock()
        mock_pubmed.search = AsyncMock(return_value=["12345", "67890"])
        mock_pubmed.fetch_details = AsyncMock(return_value=sample_articles)

        state = _make_sample_state()

        with patch.object(ipa, "PubMedClient", return_value=mock_pubmed):
            result = await ipa.search_literature(state)

        assert "pubmed_results" in result
        assert len(result["pubmed_results"]) == 2
        assert result["pubmed_results"][0]["pmid"] == "12345"

    @pytest.mark.asyncio
    async def test_builds_query_from_disease_and_area(self):
        """The PubMed query includes disease_state and therapeutic_area."""
        mock_pubmed = MagicMock()
        mock_pubmed.search = AsyncMock(return_value=[])
        mock_pubmed.fetch_details = AsyncMock(return_value=[])

        state = _make_sample_state(
            disease_state="atrial fibrillation",
            therapeutic_area="electrophysiology",
        )

        with patch.object(ipa, "PubMedClient", return_value=mock_pubmed):
            await ipa.search_literature(state)

        call_args = mock_pubmed.search.call_args
        query = call_args[0][0] if call_args[0] else call_args[1].get("query", "")
        assert "atrial fibrillation" in query
        assert "electrophysiology" in query

    @pytest.mark.asyncio
    async def test_handles_pubmed_failure_gracefully(self):
        """PubMed failure returns empty results + error record."""
        mock_pubmed = MagicMock()
        mock_pubmed.search = AsyncMock(side_effect=Exception("PubMed API timeout"))

        state = _make_sample_state()

        with patch.object(ipa, "PubMedClient", return_value=mock_pubmed):
            result = await ipa.search_literature(state)

        assert result["pubmed_results"] == []
        assert len(result["errors"]) == 1
        assert "PubMed" in result["errors"][0]["error"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestSearchLiterature -v`
Expected: FAIL — `NotImplementedError: Task 2`

- [ ] **Step 3: Implement search_literature**

Replace the `search_literature` function in `intake_prefill_agent.py`:

```python
@traceable(name="intake_prefill.search_literature", run_type="chain")
@traced_node("intake_prefill", "search_literature")
async def search_literature(state: IntakePrefillState) -> dict:
    """Search PubMed for literature relevant to the disease state."""
    disease = state["disease_state"]
    area = state["therapeutic_area"]
    audiences = state.get("target_audience_primary", [])
    query = f"{disease} {area} {' '.join(audiences)}".strip()

    pubmed = PubMedClient()
    try:
        pmids = await asyncio.wait_for(
            pubmed.search(query, max_results=20, years=5),
            timeout=30,
        )
        articles = await asyncio.wait_for(
            pubmed.fetch_details(pmids[:20]),
            timeout=60,
        )
        return {"pubmed_results": articles}
    except Exception as e:
        logger.warning("PubMed search failed: %s", e)
        return {
            "pubmed_results": [],
            "errors": list(state.get("errors", [])) + [
                {"node": "search_literature", "error": f"PubMed search failed: {e}"}
            ],
        }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestSearchLiterature -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py
git commit -m "feat(intake-prefill): implement search_literature node with PubMed client"
```

---

## Task 3: build_context Node

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py`
- Modify: `langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py`

- [ ] **Step 1: Write the failing tests for build_context**

Append to `tests/test_intake_prefill.py`:

```python
# ---------------------------------------------------------------------------
# build_context node tests
# ---------------------------------------------------------------------------

class TestBuildContext:
    """Tests for build_context node (no LLM call — pure data transformation)."""

    @pytest.mark.asyncio
    async def test_builds_context_from_articles(self):
        """Articles are formatted into a research context string."""
        articles = [
            {
                "pmid": "11111",
                "title": "SGLT2 Inhibitors in HFrEF",
                "abstract": "SGLT2i showed significant reduction in hospitalization.",
                "year": 2025,
                "journal": "NEJM",
                "journal_abbrev": "N Engl J Med",
            },
        ]
        state = _make_sample_state(pubmed_results=articles)
        result = await ipa.build_context(state)

        assert "research_context" in result
        assert "SGLT2 Inhibitors in HFrEF" in result["research_context"]
        assert "heart failure" in result["research_context"].lower()
        assert "research_summary" in result
        assert "1" in result["research_summary"]  # "Reviewed 1 recent publications"

    @pytest.mark.asyncio
    async def test_empty_articles_returns_fallback_context(self):
        """No PubMed results produces a fallback context string."""
        state = _make_sample_state(pubmed_results=[])
        result = await ipa.build_context(state)

        assert "research_context" in result
        assert "no pubmed results" in result["research_context"].lower() or \
               "general medical knowledge" in result["research_context"].lower()

    @pytest.mark.asyncio
    async def test_context_includes_audience_and_hcp_types(self):
        """Research context includes target audience and HCP types."""
        articles = [{"pmid": "1", "title": "Test", "abstract": "...", "year": 2025, "journal": "", "journal_abbrev": ""}]
        state = _make_sample_state(
            pubmed_results=articles,
            target_audience_primary=["primary care physicians"],
            target_hcp_types=["MD/DO", "NP"],
        )
        result = await ipa.build_context(state)

        assert "primary care physicians" in result["research_context"]
        assert "MD/DO" in result["research_context"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestBuildContext -v`
Expected: FAIL — `NotImplementedError: Task 3`

- [ ] **Step 3: Implement build_context**

Replace the `build_context` function in `intake_prefill_agent.py`:

```python
@traceable(name="intake_prefill.build_context", run_type="chain")
@traced_node("intake_prefill", "build_context")
async def build_context(state: IntakePrefillState) -> dict:
    """Parse PubMed results into a structured research context string. No LLM call."""
    articles = state.get("pubmed_results", [])
    disease = state["disease_state"]
    area = state["therapeutic_area"]
    audiences = ", ".join(state.get("target_audience_primary", []))
    hcp_types = ", ".join(state.get("target_hcp_types", []))

    if not articles:
        return {
            "research_context": (
                f"No PubMed results found for {disease}. "
                f"Generate based on general medical knowledge of {area}."
            ),
            "research_summary": f"No recent publications found for {disease}.",
        }

    context_parts = []
    for i, article in enumerate(articles[:15], 1):
        title = article.get("title", "Untitled")
        year = article.get("year", "N/A")
        journal = article.get("journal_abbrev") or article.get("journal", "")
        abstract = article.get("abstract", "No abstract available")
        context_parts.append(
            f"[{i}] {title} ({year})\n"
            f"Journal: {journal}\n"
            f"Abstract: {abstract}\n"
        )

    context = (
        f"DISEASE STATE: {disease}\n"
        f"THERAPEUTIC AREA: {area}\n"
        f"TARGET AUDIENCE: {audiences}\n"
        f"HCP TYPES: {hcp_types}\n\n"
        f"LITERATURE REVIEW ({len(articles)} articles):\n\n"
        + "\n".join(context_parts)
    )

    summary = (
        f"Reviewed {len(articles)} recent publications on "
        f"{disease} in {area}."
    )

    return {"research_context": context, "research_summary": summary}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestBuildContext -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py
git commit -m "feat(intake-prefill): implement build_context node — template-based context assembly"
```

---

## Task 4: generate_prefill Node

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py`
- Modify: `langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py`

- [ ] **Step 1: Write the failing tests for generate_prefill**

Append to `tests/test_intake_prefill.py`:

```python
# ---------------------------------------------------------------------------
# generate_prefill node tests
# ---------------------------------------------------------------------------

MOCK_LLM_JSON_RESPONSE = json.dumps({
    "section_b": {
        "supporter_name": "",
        "supporter_contact_name": None,
        "supporter_contact_email": None,
        "grant_amount_requested": 75000,
        "grant_submission_deadline": None,
    },
    "section_c": {
        "learning_format": "live-symposium",
        "duration_minutes": 90,
        "include_post_test": True,
        "include_pre_test": True,
        "faculty_count": 3,
    },
    "section_d": {
        "clinical_topics": ["GDMT optimization", "SGLT2 inhibitors", "Device therapy"],
        "treatment_modalities": ["Pharmacologic", "Device"],
        "patient_population": "Adults with HFrEF (EF <= 40%)",
        "stage_of_disease": "Chronic, stable",
        "comorbidities": ["Diabetes", "CKD", "Hypertension"],
    },
    "section_e": {
        "knowledge_gaps": ["Underutilization of ARNI therapy", "Delayed SGLT2i initiation"],
        "competence_gaps": ["Risk stratification for device therapy"],
        "performance_gaps": ["Failure to titrate to target doses"],
        "gap_evidence_sources": ["ACC/AHA 2022 Guidelines", "CHAMP-HF Registry"],
        "gap_priority": "high",
    },
    "section_f": {
        "primary_outcomes": ["Increase in GDMT prescription rates"],
        "secondary_outcomes": ["Improvement in dose titration to target"],
        "measurement_approach": "Pre/post knowledge assessment with 60-day practice survey",
        "moore_levels_target": [3, 4, 5],
        "follow_up_timeline": "60 days post-activity",
    },
    "section_g": {
        "key_messages": ["GDMT should be initiated early", "SGLT2i benefit is class-wide"],
        "required_references": ["PMID:12345 - DAPA-HF trial", "PMID:67890 - EMPEROR-Reduced"],
        "excluded_topics": None,
        "competitor_products_to_mention": None,
        "regulatory_considerations": "Off-label discussion of combination therapy",
    },
    "section_h": {
        "distribution_channels": ["Medical society meetings", "Online CME platforms"],
        "geo_restrictions": None,
        "language_requirements": ["English"],
        "target_launch_date": None,
        "expiration_date": None,
    },
    "confidence": {
        "section_b": "low",
        "section_c": "medium",
        "section_d": "high",
        "section_e": "high",
        "section_f": "high",
        "section_g": "high",
        "section_h": "medium",
    },
})


def _mock_llm_generate(content: str):
    """Build a mock for LLMClient.generate that returns given content."""
    return AsyncMock(return_value={
        "content": content,
        "input_tokens": 500,
        "output_tokens": 800,
        "total_tokens": 1300,
        "cost": 0.0135,
    })


class TestGeneratePrefill:
    """Tests for generate_prefill node (mocked LLM)."""

    @pytest.mark.asyncio
    async def test_parses_valid_json_response(self):
        """Valid JSON from LLM is parsed into prefill_sections and confidence."""
        state = _make_sample_state(
            research_context="LITERATURE REVIEW (5 articles): ...",
        )

        with patch.object(ipa.llm, "generate", _mock_llm_generate(MOCK_LLM_JSON_RESPONSE)):
            result = await ipa.generate_prefill(state)

        assert "prefill_sections" in result
        assert "section_d" in result["prefill_sections"]
        assert result["prefill_sections"]["section_d"]["clinical_topics"][0] == "GDMT optimization"
        assert "confidence" in result
        assert result["confidence"]["section_d"] == "high"

    @pytest.mark.asyncio
    async def test_accumulates_token_counts(self):
        """Token counts are added to running totals."""
        state = _make_sample_state(
            research_context="...",
            total_tokens=100,
            total_cost=0.001,
        )

        with patch.object(ipa.llm, "generate", _mock_llm_generate(MOCK_LLM_JSON_RESPONSE)):
            result = await ipa.generate_prefill(state)

        assert result["total_tokens"] == 100 + 1300
        assert result["total_cost"] > 0.001

    @pytest.mark.asyncio
    async def test_handles_markdown_fenced_json(self):
        """LLM wrapping JSON in ```json fences is handled."""
        fenced = "```json\n" + MOCK_LLM_JSON_RESPONSE + "\n```"
        state = _make_sample_state(research_context="...")

        with patch.object(ipa.llm, "generate", _mock_llm_generate(fenced)):
            result = await ipa.generate_prefill(state)

        assert "section_d" in result["prefill_sections"]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error(self):
        """LLM call failure returns empty sections + error record."""
        state = _make_sample_state(research_context="...")
        mock_gen = AsyncMock(side_effect=Exception("LLM timeout"))

        with patch.object(ipa.llm, "generate", mock_gen):
            result = await ipa.generate_prefill(state)

        assert result["prefill_sections"] == {}
        assert len(result["errors"]) == 1
        assert "LLM" in result["errors"][0]["error"] or "timeout" in result["errors"][0]["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error(self):
        """Unparseable LLM output returns empty sections + error record."""
        state = _make_sample_state(research_context="...")

        with patch.object(ipa.llm, "generate", _mock_llm_generate("This is not JSON at all")):
            result = await ipa.generate_prefill(state)

        assert result["prefill_sections"] == {}
        assert len(result["errors"]) >= 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestGeneratePrefill -v`
Expected: FAIL — `NotImplementedError: Task 4`

- [ ] **Step 3: Implement generate_prefill**

Replace the `generate_prefill` function in `intake_prefill_agent.py`:

```python
PREFILL_SYSTEM_PROMPT = """You are a CME (Continuing Medical Education) intake form assistant.
Based on project information and a literature review, generate draft values for sections B through H of a CME intake form.
Return ONLY a JSON object — no markdown fences, no additional text."""

PREFILL_USER_TEMPLATE = """PROJECT INFORMATION:
- Project Name: {project_name}
- Therapeutic Area: {therapeutic_area}
- Disease State: {disease_state}
- Target Audience: {target_audience}
- HCP Types: {hcp_types}

{research_context}

Generate a JSON object with this structure. Use the literature review to ground suggestions in evidence. For fields you cannot confidently suggest, use null.

{{
  "section_b": {{
    "supporter_name": "",
    "supporter_contact_name": null,
    "supporter_contact_email": null,
    "grant_amount_requested": <typical grant amount as number or null>,
    "grant_submission_deadline": null
  }},
  "section_c": {{
    "learning_format": "<webinar|live-symposium|enduring-module|workshop>",
    "duration_minutes": <integer>,
    "include_post_test": <true|false>,
    "include_pre_test": <true|false>,
    "faculty_count": <integer>
  }},
  "section_d": {{
    "clinical_topics": ["<topic>", ...],
    "treatment_modalities": ["<modality>", ...],
    "patient_population": "<description>",
    "stage_of_disease": "<description or null>",
    "comorbidities": ["<comorbidity>", ...]
  }},
  "section_e": {{
    "knowledge_gaps": ["<gap>", ...],
    "competence_gaps": ["<gap>", ...],
    "performance_gaps": ["<gap>", ...],
    "gap_evidence_sources": ["<source>", ...],
    "gap_priority": "<high|medium|low>"
  }},
  "section_f": {{
    "primary_outcomes": ["<outcome>", ...],
    "secondary_outcomes": ["<outcome>", ...],
    "measurement_approach": "<description>",
    "moore_levels_target": [<integers from 1-7>],
    "follow_up_timeline": "<timeline>"
  }},
  "section_g": {{
    "key_messages": ["<message>", ...],
    "required_references": ["PMID:<id> - <brief description>", ...],
    "excluded_topics": null,
    "competitor_products_to_mention": null,
    "regulatory_considerations": "<notes or null>"
  }},
  "section_h": {{
    "distribution_channels": ["<channel>", ...],
    "geo_restrictions": null,
    "language_requirements": ["English"],
    "target_launch_date": null,
    "expiration_date": null
  }},
  "confidence": {{
    "section_b": "low",
    "section_c": "<high|medium|low>",
    "section_d": "<high|medium|low>",
    "section_e": "<high|medium|low>",
    "section_f": "<high|medium|low>",
    "section_g": "<high|medium|low>",
    "section_h": "<high|medium|low>"
  }}
}}"""


@traceable(name="intake_prefill.generate_prefill", run_type="chain")
@traced_node("intake_prefill", "generate_prefill")
async def generate_prefill(state: IntakePrefillState) -> dict:
    """Single LLM call to generate draft values for sections B-H."""
    prompt = PREFILL_USER_TEMPLATE.format(
        project_name=state["project_name"],
        therapeutic_area=state["therapeutic_area"],
        disease_state=state["disease_state"],
        target_audience=", ".join(state.get("target_audience_primary", [])),
        hcp_types=", ".join(state.get("target_hcp_types", [])),
        research_context=state.get("research_context", ""),
    )

    try:
        response = await asyncio.wait_for(
            llm.generate(PREFILL_SYSTEM_PROMPT, prompt),
            timeout=300,
        )
    except Exception as e:
        logger.error("LLM call failed in generate_prefill: %s", e)
        return {
            "prefill_sections": {},
            "confidence": {},
            "errors": list(state.get("errors", [])) + [
                {"node": "generate_prefill", "error": f"LLM call failed: {e}"}
            ],
        }

    content = response["content"].strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        first_newline = content.index("\n") if "\n" in content else 3
        content = content[first_newline + 1:]
        if content.endswith("```"):
            content = content[:-3].rstrip()

    try:
        raw = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON: %s", e)
        return {
            "prefill_sections": {},
            "confidence": {},
            "errors": list(state.get("errors", [])) + [
                {"node": "generate_prefill", "error": f"Invalid JSON from LLM: {e}"}
            ],
        }

    confidence = raw.pop("confidence", {})
    prefill_sections = {k: v for k, v in raw.items() if k.startswith("section_")}

    return {
        "prefill_sections": prefill_sections,
        "confidence": confidence,
        "total_tokens": state.get("total_tokens", 0) + response["total_tokens"],
        "total_cost": state.get("total_cost", 0.0) + response["cost"],
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestGeneratePrefill -v`
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py
git commit -m "feat(intake-prefill): implement generate_prefill node with structured JSON output"
```

---

## Task 5: validate_output Node

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py`
- Modify: `langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py`

- [ ] **Step 1: Write the failing tests for validate_output**

Append to `tests/test_intake_prefill.py`:

```python
# ---------------------------------------------------------------------------
# validate_output node tests
# ---------------------------------------------------------------------------

class TestValidateOutput:
    """Tests for validate_output node (no LLM — pure validation)."""

    @pytest.mark.asyncio
    async def test_valid_sections_pass_through(self):
        """Well-formed sections pass validation unchanged."""
        valid_sections = json.loads(MOCK_LLM_JSON_RESPONSE)
        del valid_sections["confidence"]
        state = _make_sample_state(prefill_sections=valid_sections)
        result = await ipa.validate_output(state)

        assert "section_d" in result["prefill_sections"]
        assert result["prefill_sections"]["section_d"]["clinical_topics"] == [
            "GDMT optimization", "SGLT2 inhibitors", "Device therapy"
        ]

    @pytest.mark.asyncio
    async def test_wrong_type_coerced_to_default(self):
        """Fields with wrong types are coerced to appropriate defaults."""
        bad_sections = {
            "section_c": {
                "learning_format": 12345,        # should be str — coerced to "12345"
                "duration_minutes": "ninety",     # should be int — coerced to None
                "include_post_test": "yes",       # should be bool — coerced to True
                "include_pre_test": 0,            # should be bool — coerced to False
                "faculty_count": 3,               # correct
            },
        }
        state = _make_sample_state(prefill_sections=bad_sections)
        result = await ipa.validate_output(state)

        sec_c = result["prefill_sections"]["section_c"]
        assert isinstance(sec_c["learning_format"], str)
        assert sec_c["faculty_count"] == 3

    @pytest.mark.asyncio
    async def test_missing_section_produces_error(self):
        """Sections missing entirely produce error records."""
        state = _make_sample_state(prefill_sections={"section_b": {"supporter_name": ""}})
        result = await ipa.validate_output(state)

        assert len(result["errors"]) > 0
        error_sections = [e["error"] for e in result["errors"]]
        assert any("section_c" in err for err in error_sections)

    @pytest.mark.asyncio
    async def test_empty_prefill_all_errors(self):
        """Empty prefill_sections logs errors for all 7 sections."""
        state = _make_sample_state(prefill_sections={})
        result = await ipa.validate_output(state)

        assert len(result["errors"]) == 7  # sections b through h
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestValidateOutput -v`
Expected: FAIL — `NotImplementedError: Task 5`

- [ ] **Step 3: Implement validate_output**

Replace the `validate_output` function in `intake_prefill_agent.py`:

```python
# Section field schemas: field_name -> tuple of acceptable types
SECTION_SCHEMAS: Dict[str, Dict[str, tuple]] = {
    "section_b": {
        "supporter_name": (str,),
        "supporter_contact_name": (str, type(None)),
        "supporter_contact_email": (str, type(None)),
        "grant_amount_requested": (int, float, type(None)),
        "grant_submission_deadline": (str, type(None)),
    },
    "section_c": {
        "learning_format": (str,),
        "duration_minutes": (int, type(None)),
        "include_post_test": (bool,),
        "include_pre_test": (bool,),
        "faculty_count": (int, type(None)),
    },
    "section_d": {
        "clinical_topics": (list,),
        "treatment_modalities": (list, type(None)),
        "patient_population": (str, type(None)),
        "stage_of_disease": (str, type(None)),
        "comorbidities": (list, type(None)),
    },
    "section_e": {
        "knowledge_gaps": (list, type(None)),
        "competence_gaps": (list, type(None)),
        "performance_gaps": (list, type(None)),
        "gap_evidence_sources": (list, type(None)),
        "gap_priority": (str, type(None)),
    },
    "section_f": {
        "primary_outcomes": (list, type(None)),
        "secondary_outcomes": (list, type(None)),
        "measurement_approach": (str, type(None)),
        "moore_levels_target": (list, type(None)),
        "follow_up_timeline": (str, type(None)),
    },
    "section_g": {
        "key_messages": (list, type(None)),
        "required_references": (list, type(None)),
        "excluded_topics": (list, type(None)),
        "competitor_products_to_mention": (list, type(None)),
        "regulatory_considerations": (str, type(None)),
    },
    "section_h": {
        "distribution_channels": (list, type(None)),
        "geo_restrictions": (list, type(None)),
        "language_requirements": (list, type(None)),
        "target_launch_date": (str, type(None)),
        "expiration_date": (str, type(None)),
    },
}


def _coerce_field(value: Any, accepted_types: tuple) -> Any:
    """Coerce a value to match the accepted types, or return a sensible default."""
    if isinstance(value, accepted_types):
        return value
    if type(None) in accepted_types and value is None:
        return None
    # Attempt coercions for required (non-nullable) types
    if str in accepted_types and not isinstance(value, str):
        return str(value) if value is not None else ""
    if list in accepted_types and not isinstance(value, list):
        return list(value) if isinstance(value, (list, tuple)) else []
    if bool in accepted_types and not isinstance(value, bool):
        return bool(value) if value is not None else False
    if int in accepted_types and not isinstance(value, int):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None if type(None) in accepted_types else 0
    return None


@traceable(name="intake_prefill.validate_output", run_type="chain")
@traced_node("intake_prefill", "validate_output")
async def validate_output(state: IntakePrefillState) -> dict:
    """Type-check and sanitize the LLM output against section schemas."""
    prefill = state.get("prefill_sections", {})
    validated = {}
    errors = list(state.get("errors", []))

    for section_key, schema in SECTION_SCHEMAS.items():
        section_data = prefill.get(section_key)
        if not isinstance(section_data, dict):
            errors.append({
                "node": "validate_output",
                "error": f"Missing or invalid {section_key}",
            })
            continue

        cleaned = {}
        for field_name, accepted_types in schema.items():
            value = section_data.get(field_name)
            cleaned[field_name] = _coerce_field(value, accepted_types)
        validated[section_key] = cleaned

    return {"prefill_sections": validated, "errors": errors}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py::TestValidateOutput -v`
Expected: 4 PASSED

- [ ] **Step 5: Run all agent tests**

Run: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py -v`
Expected: All 17 tests PASSED (2 structure + 3 search + 3 context + 5 generate + 4 validate)

- [ ] **Step 6: Commit**

```bash
git add langgraph_workflows/dhg-agents-cloud/src/intake_prefill_agent.py langgraph_workflows/dhg-agents-cloud/tests/test_intake_prefill.py
git commit -m "feat(intake-prefill): implement validate_output node with type coercion and schema validation"
```

---

## Task 6: Register Agent in LangGraph

**Files:**
- Modify: `langgraph_workflows/dhg-agents-cloud/langgraph.json`

- [ ] **Step 1: Add intake_prefill to langgraph.json**

Add the `intake_prefill` entry to the `graphs` object in `langgraph_workflows/dhg-agents-cloud/langgraph.json`. The file currently has 17 graphs; this adds the 18th:

```json
{
  "dependencies": ["."],
  "graphs": {
    "needs_assessment": "./src/needs_assessment_agent.py:graph",
    "prose_quality": "./src/prose_quality_agent.py:graph",
    "research": "./src/research_agent.py:graph",
    "clinical_practice": "./src/clinical_practice_agent.py:graph",
    "gap_analysis": "./src/gap_analysis_agent.py:graph",
    "learning_objectives": "./src/learning_objectives_agent.py:graph",
    "curriculum_design": "./src/curriculum_design_agent.py:graph",
    "research_protocol": "./src/research_protocol_agent.py:graph",
    "marketing_plan": "./src/marketing_plan_agent.py:graph",
    "grant_writer": "./src/grant_writer_agent.py:graph",
    "compliance_review": "./src/compliance_review_agent.py:graph",
    "citation_checker": "./src/citation_checker_agent.py:graph",
    "registry": "./src/registry_agent.py:graph",
    "intake_prefill": "./src/intake_prefill_agent.py:graph",
    "needs_package": "./src/orchestrator.py:needs_graph",
    "curriculum_package": "./src/orchestrator.py:curriculum_graph",
    "grant_package": "./src/orchestrator.py:grant_graph",
    "full_pipeline": "./src/orchestrator.py:full_graph"
  },
  "env": "runtime.env"
}
```

- [ ] **Step 2: Verify the JSON is valid**

Run: `python3 -c "import json; json.load(open('langgraph_workflows/dhg-agents-cloud/langgraph.json')); print('Valid JSON')" `
Expected: `Valid JSON`

- [ ] **Step 3: Commit**

```bash
git add langgraph_workflows/dhg-agents-cloud/langgraph.json
git commit -m "feat(intake-prefill): register intake_prefill graph in langgraph.json"
```

---

## Task 7: Registry API Prefill Endpoint

**Files:**
- Modify: `registry/test_cme_endpoints.py`
- Modify: `registry/cme_endpoints.py`

- [ ] **Step 1: Write the failing tests for the prefill endpoint**

Add the following test class to `registry/test_cme_endpoints.py`:

```python
class TestIntakePrefill:
    """Tests for POST /api/cme/intake/prefill."""

    def test_prefill_requires_body(self, client):
        response = client.post("/api/cme/intake/prefill")
        assert response.status_code == 422

    def test_prefill_rejects_incomplete_section_a(self, client):
        """Missing required fields in Section A returns 422."""
        response = client.post(
            "/api/cme/intake/prefill",
            json={"project_name": "Test"},
        )
        assert response.status_code == 422

    def test_prefill_rejects_short_project_name(self, client):
        """Project name under 5 chars returns 422."""
        response = client.post(
            "/api/cme/intake/prefill",
            json={
                "project_name": "Hi",
                "therapeutic_area": "cardiology",
                "disease_state": "heart failure",
                "target_audience_primary": ["cardiologists"],
            },
        )
        assert response.status_code == 422

    @patch("cme_endpoints.trigger_intake_prefill")
    def test_prefill_success(self, mock_trigger, client):
        """Valid Section A payload invokes the prefill agent and returns 200."""
        mock_trigger.return_value = {
            "prefill_sections": {
                "section_b": {"supporter_name": ""},
                "section_c": {"learning_format": "webinar"},
            },
            "research_summary": "Reviewed 10 articles on heart failure.",
            "confidence": {"section_b": "low", "section_c": "medium"},
        }
        response = client.post(
            "/api/cme/intake/prefill",
            json={
                "project_name": "HFrEF GDMT Update",
                "therapeutic_area": "cardiology",
                "disease_state": "heart failure",
                "target_audience_primary": ["cardiologists"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "prefill_sections" in body
        assert "research_summary" in body
        assert "confidence" in body
        mock_trigger.assert_called_once()

    @patch("cme_endpoints.trigger_intake_prefill")
    def test_prefill_agent_failure_returns_502(self, mock_trigger, client):
        """Agent failure returns 502 with error message."""
        mock_trigger.side_effect = Exception("LangGraph Cloud timeout")
        response = client.post(
            "/api/cme/intake/prefill",
            json={
                "project_name": "HFrEF GDMT Update",
                "therapeutic_area": "cardiology",
                "disease_state": "heart failure",
                "target_audience_primary": ["cardiologists"],
            },
        )
        assert response.status_code == 502
        assert "prefill" in response.json()["detail"].lower() or \
               "unavailable" in response.json()["detail"].lower()
```

Add `from unittest.mock import patch` to the imports at the top of `registry/test_cme_endpoints.py` if not already present.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd registry && python -m pytest test_cme_endpoints.py::TestIntakePrefill -v`
Expected: FAIL — `404 Not Found` (endpoint doesn't exist yet) or import errors

- [ ] **Step 3: Add the prefill request model, helper function, and endpoint to cme_endpoints.py**

Add the `PrefillRequest` model after the existing Section models (around line 169 after `IntakeSubmission`):

```python
class PrefillRequest(BaseModel):
    """Section A fields needed to trigger intake prefill."""
    project_name: str = Field(..., min_length=5, max_length=200)
    therapeutic_area: str = Field(..., min_length=1, max_length=200)
    disease_state: str = Field(..., min_length=1, max_length=200)
    target_audience_primary: List[str] = Field(..., min_length=1, max_length=5)
    target_hcp_types: Optional[List[str]] = Field(None)
```

Add the `trigger_intake_prefill` helper function after `trigger_langgraph_pipeline` (around line 291):

```python
async def trigger_intake_prefill(payload: dict) -> dict:
    """
    Invoke the intake_prefill graph on LangGraph Cloud and wait for result.
    Uses the /runs/wait endpoint to block until completion (60s timeout).
    """
    langgraph_url = os.getenv("LANGGRAPH_API_URL", LANGGRAPH_CLOUD_URL)
    langchain_api_key = os.getenv("LANGCHAIN_API_KEY", "")
    headers = {"x-api-key": langchain_api_key}

    async with httpx.AsyncClient(timeout=90.0) as client:
        # Create a thread
        thread_resp = await client.post(
            f"{langgraph_url}/threads",
            json={"metadata": {"graph_id": "intake_prefill"}},
            headers=headers,
        )
        thread_resp.raise_for_status()
        thread_id = thread_resp.json()["thread_id"]

        # Start a run and wait for completion
        run_resp = await client.post(
            f"{langgraph_url}/threads/{thread_id}/runs/wait",
            json={
                "assistant_id": "intake_prefill",
                "input": payload,
            },
            headers=headers,
            timeout=90.0,
        )
        run_resp.raise_for_status()
        result = run_resp.json()

        return {
            "prefill_sections": result.get("prefill_sections", {}),
            "research_summary": result.get("research_summary", ""),
            "confidence": result.get("confidence", {}),
        }
```

Add the endpoint to the CME router (find the existing router, typically near the endpoints section):

```python
@cme_router.post("/intake/prefill")
async def prefill_intake(request: PrefillRequest):
    """
    AI-powered prefill for CME intake sections B-H.
    Takes Section A fields, queries PubMed, generates structured drafts.
    """
    payload = {
        "project_name": request.project_name,
        "therapeutic_area": request.therapeutic_area,
        "disease_state": request.disease_state,
        "target_audience_primary": request.target_audience_primary,
        "target_hcp_types": request.target_hcp_types or [],
    }
    try:
        result = await trigger_intake_prefill(payload)
        return result
    except Exception as e:
        logger.error("Intake prefill failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Prefill unavailable — the AI agent could not complete the request.",
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd registry && python -m pytest test_cme_endpoints.py::TestIntakePrefill -v`
Expected: 5 PASSED

- [ ] **Step 5: Run the full registry test suite to check for regressions**

Run: `cd registry && python -m pytest test_cme_endpoints.py -v`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add registry/cme_endpoints.py registry/test_cme_endpoints.py
git commit -m "feat(intake-prefill): add POST /api/cme/intake/prefill registry endpoint"
```

---

## Task 8: Frontend Types + API Client

**Files:**
- Modify: `frontend/src/types/cme.ts`
- Modify: `frontend/src/lib/registryApi.ts`

- [ ] **Step 1: Add PrefillResponse interface to types/cme.ts**

Add after the existing `HybridSearchRequest` interface (near the end of the file):

```typescript
// =============================================================================
// INTAKE PREFILL
// =============================================================================

export type PrefillConfidence = "high" | "medium" | "low";

export interface PrefillResponse {
  prefill_sections: {
    section_b?: Partial<SectionB>;
    section_c?: Partial<SectionC>;
    section_d?: Partial<SectionD>;
    section_e?: Partial<SectionE>;
    section_f?: Partial<SectionF>;
    section_g?: Partial<SectionG>;
    section_h?: Partial<SectionH>;
  };
  research_summary: string;
  confidence: Record<string, PrefillConfidence>;
}
```

- [ ] **Step 2: Add prefillIntake function to registryApi.ts**

Add the import of `PrefillResponse` to the top import block:

```typescript
import type {
  IntakeSubmission,
  CMEProjectCreateResponse,
  CMEProjectDetail,
  ExecutionStatus,
  AgentOutput,
  CMEProjectStatus,
  SearchResponse,
  HybridSearchRequest,
  PrefillResponse,
  SectionA,
} from "@/types/cme";
```

Add the function at the end of the file, before any closing exports:

```typescript
// =============================================================================
// INTAKE PREFILL
// =============================================================================

export async function prefillIntake(
  sectionA: SectionA,
): Promise<PrefillResponse> {
  return apiFetch<PrefillResponse>("/api/cme/intake/prefill", {
    method: "POST",
    body: JSON.stringify({
      project_name: sectionA.project_name,
      therapeutic_area: sectionA.therapeutic_area,
      disease_state: sectionA.disease_state,
      target_audience_primary: sectionA.target_audience_primary,
      target_hcp_types: sectionA.target_hcp_types,
    }),
  });
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors in the modified files

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/cme.ts frontend/src/lib/registryApi.ts
git commit -m "feat(intake-prefill): add PrefillResponse type and prefillIntake API function"
```

---

## Task 9: Frontend Store — Prefill State

**Files:**
- Modify: `frontend/src/stores/intake-store.ts`

- [ ] **Step 1: Add prefill state fields and actions to intake-store.ts**

Replace the entire file contents of `frontend/src/stores/intake-store.ts`:

```typescript
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { IntakeSubmission, PrefillConfidence } from "@/types/cme";

function createEmptyIntake(): IntakeSubmission {
  return {
    section_a: {
      project_name: "",
      therapeutic_area: "",
      disease_state: "",
      target_audience_primary: [],
    },
    section_b: { supporter_name: "" },
    section_c: { learning_format: "", include_post_test: false, include_pre_test: false },
    section_d: { clinical_topics: [] },
    section_e: {},
    section_f: {},
    section_g: {},
    section_h: {},
    section_i: {
      accme_compliant: true,
      financial_disclosure_required: true,
      off_label_discussion: false,
      commercial_support_acknowledgment: true,
    },
    section_j: {},
  };
}

type PrefillSectionStatus = "prefilled" | "accepted" | "cleared";

const PREFILLABLE_SECTIONS = ["b", "c", "d", "e", "f", "g", "h"] as const;

interface IntakeState {
  intake: IntakeSubmission;
  activeSection: string;

  // Prefill state
  prefillStatus: Record<string, PrefillSectionStatus>;
  researchSummary: string | null;
  prefillConfidence: Record<string, PrefillConfidence>;

  // Actions
  setIntake: (intake: IntakeSubmission) => void;
  updateIntake: (updater: (prev: IntakeSubmission) => IntakeSubmission) => void;
  setActiveSection: (section: string) => void;
  reset: () => void;

  // Prefill actions
  applyPrefill: (
    sections: Record<string, Record<string, unknown>>,
    summary: string,
    confidence: Record<string, PrefillConfidence>,
  ) => void;
  acceptSection: (sectionId: string) => void;
  clearSection: (sectionId: string) => void;
  acceptAll: () => void;
  clearAll: () => void;
}

export const useIntakeStore = create<IntakeState>()(
  persist(
    (set) => ({
      intake: createEmptyIntake(),
      activeSection: "a",
      prefillStatus: {},
      researchSummary: null,
      prefillConfidence: {},

      setIntake: (intake) => set({ intake }),
      updateIntake: (updater) => set((s) => ({ intake: updater(s.intake) })),
      setActiveSection: (activeSection) => set({ activeSection }),
      reset: () =>
        set({
          intake: createEmptyIntake(),
          activeSection: "a",
          prefillStatus: {},
          researchSummary: null,
          prefillConfidence: {},
        }),

      applyPrefill: (sections, summary, confidence) =>
        set((s) => {
          const next = { ...s.intake };
          const status: Record<string, PrefillSectionStatus> = {};

          for (const id of PREFILLABLE_SECTIONS) {
            const key = `section_${id}` as keyof IntakeSubmission;
            const data = sections[key];
            if (data && typeof data === "object") {
              (next as Record<string, unknown>)[key] = {
                ...(next[key] as Record<string, unknown>),
                ...data,
              };
              status[id] = "prefilled";
            }
          }

          return {
            intake: next,
            prefillStatus: status,
            researchSummary: summary,
            prefillConfidence: confidence,
          };
        }),

      acceptSection: (sectionId) =>
        set((s) => ({
          prefillStatus: { ...s.prefillStatus, [sectionId]: "accepted" as const },
        })),

      clearSection: (sectionId) =>
        set((s) => {
          const key = `section_${sectionId}` as keyof IntakeSubmission;
          const empty = createEmptyIntake();
          return {
            intake: { ...s.intake, [key]: empty[key] },
            prefillStatus: { ...s.prefillStatus, [sectionId]: "cleared" as const },
          };
        }),

      acceptAll: () =>
        set((s) => {
          const updated: Record<string, PrefillSectionStatus> = {};
          for (const [id, status] of Object.entries(s.prefillStatus)) {
            updated[id] = status === "prefilled" ? "accepted" : status;
          }
          return { prefillStatus: updated };
        }),

      clearAll: () =>
        set(() => {
          const empty = createEmptyIntake();
          return {
            intake: { ...empty },
            prefillStatus: {},
            researchSummary: null,
            prefillConfidence: {},
          };
        }),
    }),
    {
      name: "dhg-intake-draft",
    },
  ),
);
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/intake-store.ts
git commit -m "feat(intake-prefill): add prefill state tracking, accept/clear actions to intake store"
```

---

## Task 10: Frontend UI — Section Nav AI Draft Indicators

**Files:**
- Modify: `frontend/src/components/intake/section-nav.tsx`

**Design fixes applied (from frontend review):**
- Width stays at 180px (no layout shift from existing pages)
- All purple colors use `text-primary` / `bg-primary` semantic tokens (auto dark mode)
- Confidence uses H/M/L text labels (matches section-a-basics tier pattern, WCAG compliant)
- Interactive targets meet 24px minimum (WCAG 2.5.8)
- All interactive elements have `aria-label` attributes
- No hard-coded `dark:` color overrides — semantic tokens handle both modes

- [ ] **Step 1: Update section-nav.tsx with AI Draft indicators and per-section controls**

Replace the entire file contents of `frontend/src/components/intake/section-nav.tsx`:

```tsx
"use client";

import { cn } from "@/lib/utils";
import { Check, Sparkles, X } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import type { PrefillConfidence } from "@/types/cme";

export interface SectionDef {
  id: string;
  label: string;
  required: boolean;
}

export const SECTIONS: SectionDef[] = [
  { id: "a", label: "A. Project Basics", required: true },
  { id: "b", label: "B. Supporter", required: false },
  { id: "c", label: "C. Educational Design", required: false },
  { id: "d", label: "D. Clinical Focus", required: false },
  { id: "e", label: "E. Educational Gaps", required: false },
  { id: "f", label: "F. Outcomes", required: false },
  { id: "g", label: "G. Content", required: false },
  { id: "h", label: "H. Logistics", required: false },
  { id: "i", label: "I. Compliance", required: false },
  { id: "j", label: "J. Additional", required: false },
];

type PrefillSectionStatus = "prefilled" | "accepted" | "cleared";

interface SectionNavProps {
  activeSection: string;
  onSelect: (id: string) => void;
  completedSections: Set<string>;
  prefillStatus?: Record<string, PrefillSectionStatus>;
  prefillConfidence?: Record<string, PrefillConfidence>;
  onAcceptSection?: (id: string) => void;
  onClearSection?: (id: string) => void;
}

const CONFIDENCE_DISPLAY: Record<PrefillConfidence, { letter: string; className: string; label: string }> = {
  high: { letter: "H", className: "text-green-500", label: "High confidence" },
  medium: { letter: "M", className: "text-amber-500", label: "Medium confidence" },
  low: { letter: "L", className: "text-destructive", label: "Low confidence" },
};

export function SectionNav({
  activeSection,
  onSelect,
  completedSections,
  prefillStatus = {},
  prefillConfidence = {},
  onAcceptSection,
  onClearSection,
}: SectionNavProps) {
  const progress = Math.round((completedSections.size / SECTIONS.length) * 100);

  return (
    <div className="w-[180px] shrink-0 border-r border-border p-4 space-y-3">
      <div className="space-y-1">
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <Progress value={progress} className="h-1.5" />
      </div>
      <nav className="space-y-0.5">
        {SECTIONS.map((section) => {
          const status = prefillStatus[section.id];
          const confidence = prefillConfidence[`section_${section.id}`];
          const isPrefilled = status === "prefilled";
          const confidenceInfo = confidence ? CONFIDENCE_DISPLAY[confidence] : null;

          return (
            <div key={section.id}>
              <button
                type="button"
                onClick={() => onSelect(section.id)}
                className={cn(
                  "flex items-center gap-2 w-full text-left px-2 py-1.5 rounded-md text-xs transition-colors",
                  activeSection === section.id
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground hover:bg-muted",
                )}
              >
                {completedSections.has(section.id) ? (
                  <Check className="h-3 w-3 shrink-0 text-green-500" />
                ) : isPrefilled ? (
                  <Sparkles className="h-3 w-3 shrink-0 text-primary" aria-hidden="true" />
                ) : (
                  <span className="h-3 w-3 shrink-0 rounded-full border border-border" />
                )}
                <span className="truncate">{section.label}</span>
                {section.required && (
                  <span className="text-[8px] text-destructive ml-auto" aria-label="Required">*</span>
                )}
                {isPrefilled && confidenceInfo && (
                  <span
                    className={cn("text-[10px] font-semibold ml-auto", confidenceInfo.className)}
                    title={confidenceInfo.label}
                    aria-label={confidenceInfo.label}
                  >
                    {confidenceInfo.letter}
                  </span>
                )}
              </button>

              {isPrefilled && (
                <div className="flex items-center gap-1.5 pl-7 py-0.5">
                  <span className="text-[10px] text-primary font-medium">AI Draft</span>
                  {onAcceptSection && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onAcceptSection(section.id);
                      }}
                      className="text-[10px] text-green-500 hover:underline ml-auto min-h-6 flex items-center"
                      aria-label={`Accept AI draft for ${section.label}`}
                    >
                      Accept
                    </button>
                  )}
                  {onClearSection && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onClearSection(section.id);
                      }}
                      className="text-muted-foreground hover:text-destructive min-h-6 min-w-6 flex items-center justify-center"
                      aria-label={`Clear AI draft for ${section.label}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors (the new props are optional, so existing callers are unaffected)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/intake/section-nav.tsx
git commit -m "feat(intake-prefill): add AI Draft indicators and per-section accept/clear to section nav"
```

---

## Task 11: Frontend UI — Prefill Button + Banner

**Files:**
- Modify: `frontend/src/components/intake/intake-form.tsx`

**Design fixes applied (from frontend review):**
- All purple colors use `primary` semantic token (auto dark mode, correct DHG Purple)
- Banner has entrance animation (`animate-in fade-in slide-in-from-top-2`) via tw-animate-css
- Banner has `role="status"` for screen readers
- Prefill button uses semantic `border-primary/30 text-primary` (not raw Tailwind purple)
- Accept All button uses `text-green-500` (consistent with existing Check icon in section-nav)
- Zero hard-coded `dark:` color overrides — semantic tokens handle both modes

- [ ] **Step 1: Update intake-form.tsx with prefill button, loading state, and accept/clear banner**

Replace the entire file contents of `frontend/src/components/intake/intake-form.tsx`:

```tsx
"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Loader2, Sparkles, CheckCheck, Trash2 } from "lucide-react";
import { SectionNav, SECTIONS } from "./section-nav";
import { SectionABasics } from "./section-a-basics";
import { SectionBSupporter } from "./section-b-supporter";
import { SectionCEducational } from "./section-c-educational";
import { SectionDClinical } from "./section-d-clinical";
import { SectionEGaps } from "./section-e-gaps";
import { SectionFOutcomes } from "./section-f-outcomes";
import { SectionGContent } from "./section-g-content";
import { SectionHLogistics } from "./section-h-logistics";
import { SectionICompliance } from "./section-i-compliance";
import { SectionJAdditional } from "./section-j-additional";
import type { IntakeSubmission } from "@/types/cme";
import * as registryApi from "@/lib/registryApi";
import { useIntakeStore } from "@/stores/intake-store";

function isSectionComplete(intake: IntakeSubmission, sectionId: string): boolean {
  switch (sectionId) {
    case "a": {
      const a = intake.section_a;
      return a.project_name.length >= 5 && a.therapeutic_area.length > 0 && a.disease_state.length > 0 && a.target_audience_primary.length >= 1;
    }
    case "b": return !!intake.section_b.supporter_name;
    case "c": return !!intake.section_c.learning_format;
    case "d": return intake.section_d.clinical_topics.length > 0;
    case "e": return (intake.section_e.knowledge_gaps?.length ?? 0) > 0;
    case "f": return (intake.section_f.primary_outcomes?.length ?? 0) > 0;
    case "g": return (intake.section_g.key_messages?.length ?? 0) > 0;
    case "h": return !!intake.section_h.target_launch_date;
    case "i": return true;
    case "j": return !!intake.section_j.special_instructions;
    default: return false;
  }
}

export function IntakeForm() {
  const router = useRouter();
  const {
    intake,
    updateIntake,
    activeSection,
    setActiveSection,
    reset,
    prefillStatus,
    researchSummary,
    prefillConfidence,
    applyPrefill,
    acceptSection,
    clearSection,
    acceptAll,
    clearAll,
  } = useIntakeStore();
  const [saving, setSaving] = useState(false);
  const [prefilling, setPrefilling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const completedSections = useMemo(() => {
    const set = new Set<string>();
    for (const s of SECTIONS) {
      if (isSectionComplete(intake, s.id)) set.add(s.id);
    }
    return set;
  }, [intake]);

  const canSave =
    intake.section_a.project_name.length >= 5 &&
    intake.section_a.therapeutic_area.length > 0 &&
    intake.section_a.disease_state.length > 0 &&
    intake.section_a.target_audience_primary.length >= 1;

  const hasPrefilled = Object.values(prefillStatus).some((s) => s === "prefilled");

  async function handlePrefill() {
    setPrefilling(true);
    setError(null);
    try {
      const result = await registryApi.prefillIntake(intake.section_a);
      applyPrefill(
        result.prefill_sections,
        result.research_summary,
        result.confidence,
      );
      setActiveSection("b");
    } catch (e) {
      setError("Prefill unavailable \u2014 you can fill sections manually.");
    } finally {
      setPrefilling(false);
    }
  }

  async function handleSave(startPipeline: boolean) {
    setSaving(true);
    setError(null);
    try {
      const result = await registryApi.createProject(intake);
      if (startPipeline) {
        registryApi.startPipeline(result.project_id).catch((e) => {
          console.error("Pipeline start failed:", e);
        });
      }
      reset();
      router.push(`/projects/${result.project_id}`);
    } catch (e) {
      setError((e as Error).message);
      setSaving(false);
    }
  }

  function renderSection() {
    switch (activeSection) {
      case "a": return <SectionABasics data={intake.section_a} onChange={(d) => updateIntake((p) => ({ ...p, section_a: d }))} />;
      case "b": return <SectionBSupporter data={intake.section_b} onChange={(d) => updateIntake((p) => ({ ...p, section_b: d }))} />;
      case "c": return <SectionCEducational data={intake.section_c} onChange={(d) => updateIntake((p) => ({ ...p, section_c: d }))} />;
      case "d": return <SectionDClinical data={intake.section_d} onChange={(d) => updateIntake((p) => ({ ...p, section_d: d }))} />;
      case "e": return <SectionEGaps data={intake.section_e} onChange={(d) => updateIntake((p) => ({ ...p, section_e: d }))} />;
      case "f": return <SectionFOutcomes data={intake.section_f} onChange={(d) => updateIntake((p) => ({ ...p, section_f: d }))} />;
      case "g": return <SectionGContent data={intake.section_g} onChange={(d) => updateIntake((p) => ({ ...p, section_g: d }))} />;
      case "h": return <SectionHLogistics data={intake.section_h} onChange={(d) => updateIntake((p) => ({ ...p, section_h: d }))} />;
      case "i": return <SectionICompliance data={intake.section_i} onChange={(d) => updateIntake((p) => ({ ...p, section_i: d }))} />;
      case "j": return <SectionJAdditional data={intake.section_j} onChange={(d) => updateIntake((p) => ({ ...p, section_j: d }))} />;
      default: return null;
    }
  }

  return (
    <div className="flex h-full">
      <SectionNav
        activeSection={activeSection}
        onSelect={setActiveSection}
        completedSections={completedSections}
        prefillStatus={prefillStatus}
        prefillConfidence={prefillConfidence}
        onAcceptSection={acceptSection}
        onClearSection={clearSection}
      />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Prefill banner — entrance animation via tw-animate-css */}
        {hasPrefilled && (
          <div
            role="status"
            className="mx-6 mt-4 rounded-md border border-primary/20 bg-primary/5 p-3 flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-300"
          >
            <Sparkles className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground">
                AI Draft Ready
              </p>
              {researchSummary && (
                <p className="text-xs text-muted-foreground truncate">
                  {researchSummary}
                </p>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-green-500 hover:bg-muted"
              onClick={acceptAll}
              aria-label="Accept all AI-drafted sections"
            >
              <CheckCheck className="h-3.5 w-3.5 mr-1" />
              Accept All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              onClick={clearAll}
              aria-label="Clear all AI-drafted sections"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              Clear All
            </Button>
          </div>
        )}

        <div className="flex-1 overflow-auto p-6 max-w-2xl">
          {renderSection()}
        </div>

        {error && (
          <div role="alert" className="mx-6 mb-3 rounded-md bg-destructive/10 text-destructive text-sm p-3">
            {error}
          </div>
        )}

        <div className="border-t border-border px-6 py-3 flex items-center gap-3">
          <Button variant="outline" onClick={() => router.push("/projects")} disabled={saving || prefilling}>
            Cancel
          </Button>
          <Button
            variant="outline"
            onClick={handlePrefill}
            disabled={!canSave || prefilling || saving}
            className="border-primary/30 text-primary hover:bg-primary/5"
          >
            {prefilling ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                Researching {intake.section_a.disease_state}...
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                Research &amp; Prefill
              </>
            )}
          </Button>
          <div className="flex-1" />
          <Button variant="secondary" onClick={() => handleSave(false)} disabled={!canSave || saving || prefilling}>
            {saving ? "Saving..." : "Save Draft"}
          </Button>
          <Button onClick={() => handleSave(true)} disabled={!canSave || saving || prefilling}>
            {saving ? "Starting..." : "Save & Start Pipeline"}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors

- [ ] **Step 3: Start the dev server and test the UI**

Run: `cd frontend && npm run dev`

Manual verification checklist:
1. Navigate to the intake form page
2. Section A is visible with empty fields
3. "Research & Prefill" button is visible but disabled (Section A incomplete), styled with DHG Purple accent
4. Fill in Section A: project name (5+ chars), therapeutic area, disease state, at least 1 audience
5. "Research & Prefill" button becomes enabled
6. Click it — see spinner with "Researching [disease_state]..."
7. On success: banner slides in from top with fade animation, "AI Draft Ready" displayed
8. Sections B-H populated, nav shows sparkle icons with H/M/L confidence labels
9. Per-section "Accept" / "Clear" buttons work in sidebar (min 24px touch targets)
10. "Accept All" / "Clear All" banner buttons work
11. Toggle dark mode — all AI accent colors auto-switch via semantic tokens (no visual breaks)
12. "Save Draft" and "Save & Start Pipeline" still function normally
13. Page refresh preserves prefill state (localStorage)

Note: Prefill will return 502 until the agent is deployed to LangGraph Cloud — verify the error message "Prefill unavailable" appears gracefully.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/intake/intake-form.tsx
git commit -m "feat(intake-prefill): add Research & Prefill button, banner, and accept/clear controls"
```

---

## Verification Checklist

After all tasks are complete, verify end-to-end:

- [ ] All LangGraph agent tests pass: `cd langgraph_workflows/dhg-agents-cloud && python -m pytest tests/test_intake_prefill.py -v`
- [ ] All registry tests pass: `cd registry && python -m pytest test_cme_endpoints.py -v`
- [ ] Frontend compiles: `cd frontend && npx tsc --noEmit`
- [ ] `langgraph.json` has 18 graphs (17 existing + intake_prefill)
- [ ] No regressions in existing intake form behavior (save draft, start pipeline, section navigation)
- [ ] Prefill gracefully degrades when LangGraph Cloud is unreachable (502 → "Prefill unavailable" message)
