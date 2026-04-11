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
