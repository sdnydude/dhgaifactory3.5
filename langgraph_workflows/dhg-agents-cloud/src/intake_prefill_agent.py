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
