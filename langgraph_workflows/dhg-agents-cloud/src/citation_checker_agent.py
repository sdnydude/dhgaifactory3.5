"""
DHG CME Citation Checker Agent - LangGraph Cloud
=================================================
Verifies that AMA-formatted citations in a document are real,
not retracted, and not outdated. Produces a registry_request dict
for the Registry Agent to persist verified citations.

Standalone agent. Also runs after the Research agent in the pipeline.

LANGGRAPH CLOUD READY:
- Pure LangGraph + LangSmith
- No Docker/FastAPI dependencies
- Registry persistence delegated to Registry Agent

Author: Digital Harmony Group
Version: 1.0.0
"""

import re
import json
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict

# LangGraph imports
from langgraph.graph import StateGraph, END
from langsmith import traceable

# OpenTelemetry tracing (dual-export with LangSmith)
from tracing import traced_node

# LLM
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# HTTP client for registry API and PubMed
import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

MAX_RETRIES = 3
AGENT_TIMEOUT = 300
FRESHNESS_YEARS = 10


# =============================================================================
# STATE DEFINITION
# =============================================================================

class CitationCheckerState(TypedDict):
    """State for Citation Checker agent."""

    # === INPUT ===
    topic: str
    document_text: str
    disease_state: Optional[str]
    project_id: Optional[str]

    # === PROCESSING ===
    extracted_citations: List[Dict[str, Any]]
    lookup_results: List[Dict[str, Any]]
    messages: list

    # === OUTPUT ===
    citation_results: List[Dict[str, Any]]
    trust_score: float
    executive_summary: str
    registry_request: Dict[str, Any]  # Prepared payload for Registry Agent

    # === METADATA ===
    errors: List[str]
    retry_count: int
    model_used: str
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

    @traceable(name="citation_checker_llm_call", run_type="llm")
    async def generate(self, system: str, prompt: str, metadata: dict = None) -> dict:
        """Generate response with cost tracking."""
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
        response = await asyncio.wait_for(
            self.model.ainvoke(messages, config={"metadata": metadata or {}}),
            timeout=AGENT_TIMEOUT,
        )

        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = response.usage_metadata.get("input_tokens", 0)
            output_tokens = response.usage_metadata.get("output_tokens", 0)

        cost = (input_tokens / 1000 * self.cost_per_1k_input) + (
            output_tokens / 1000 * self.cost_per_1k_output
        )

        return {
            "content": response.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
        }


llm = LLMClient()


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are a medical citation verification specialist working for a CME \
(Continuing Medical Education) accreditation organization. Your job is to verify that \
research citations are real, accurate, and current.

You work with AMA (American Medical Association) citation format. AMA format follows this \
pattern:
  Author(s). Article title. Journal Name. Year;Volume(Issue):Pages. doi:XX

Your responsibilities:
1. Extract every citation from the provided document, preserving the exact AMA formatting.
2. For each citation, identify: authors, title, journal, year, volume, issue, pages, \
DOI, and PubMed ID (PMID) if detectable.
3. Parse the publication year to assess freshness.

Rules:
- Sources older than 10 years are flagged as "outdated" UNLESS they are landmark studies \
  (seminal works that established a field, changed standard of care, or are universally \
  cited in the domain).
- Retracted papers are an automatic fail — verification_status = "retracted".
- If a citation cannot be matched to any known publication, mark it "not_found".
- Verified citations get verification_status = "verified".
- Landmark studies older than 10 years get verification_status = "landmark".

Always respond with valid JSON. No markdown fencing, no commentary outside the JSON."""

EXTRACTION_PROMPT = """Extract all AMA-formatted citations from the following document. \
For each citation, return a JSON array where each element has:
{{
  "raw_citation": "the exact citation text as it appears",
  "authors": "author list",
  "title": "article title",
  "journal": "journal name",
  "year": 2024,
  "volume": "vol",
  "issue": "issue",
  "pages": "pages",
  "doi": "doi if present",
  "pmid": "pmid if present"
}}

If a field cannot be determined, use null.

Document:
{document_text}"""

VERIFICATION_PROMPT = """You have extracted citations and looked them up. Now assess each one.

For each citation, determine:
1. verification_status: "verified", "not_found", "retracted", "outdated", or "landmark"
2. confidence: 0.0 to 1.0 — how confident are you in the verification
3. reason: one sentence explaining the status
4. is_landmark: true/false — is this a landmark study?

Rules:
- Current year is {current_year}. Sources published before {cutoff_year} are "outdated" \
  unless they are landmark studies.
- If PubMed lookup returned a match with matching title/authors/journal, it's "verified".
- If PubMed returned no match and we have no DOI confirmation, it's "not_found".
- If PubMed indicates retraction, it's "retracted".

Disease area context: {disease_state}

Citations with lookup results:
{lookup_json}

Return a JSON array with one object per citation:
{{
  "raw_citation": "original text",
  "verification_status": "verified|not_found|retracted|outdated|landmark",
  "confidence": 0.95,
  "reason": "Matched in PubMed (PMID 12345678)",
  "year": 2023,
  "pmid": "12345678",
  "doi": "10.1234/example",
  "title": "article title",
  "authors": "author list",
  "journal": "journal name",
  "is_landmark": false
}}"""

SUMMARY_PROMPT = """Write a one-paragraph executive summary of the citation verification \
results. Include:
- Total citations checked
- How many verified, not found, retracted, outdated, and landmark
- The overall trust score (provided below)
- Any specific concerns worth highlighting

Be concise and factual. No filler. Write for a busy medical education director.

Trust score: {trust_score:.0%}
Results:
{results_json}"""


# =============================================================================
# PUBMED LOOKUP
# =============================================================================

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


async def lookup_pubmed(title: str, authors: str = "", journal: str = "") -> Dict[str, Any]:
    """Search PubMed for a citation. Returns match info or empty dict."""
    query_parts = []
    if title:
        # Use first 100 chars of title for search
        clean_title = re.sub(r"[^\w\s]", "", title[:100])
        query_parts.append(f"{clean_title}[Title]")
    if journal:
        query_parts.append(f"{journal}[Journal]")

    if not query_parts:
        return {"matched": False}

    query = " AND ".join(query_parts)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            search_resp = await client.get(
                PUBMED_SEARCH_URL,
                params={
                    "db": "pubmed",
                    "term": query,
                    "retmode": "json",
                    "retmax": 3,
                },
            )
            search_resp.raise_for_status()
            search_data = search_resp.json()

            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return {"matched": False}

            # Fetch the first result to confirm
            fetch_resp = await client.get(
                PUBMED_FETCH_URL,
                params={
                    "db": "pubmed",
                    "id": id_list[0],
                    "retmode": "xml",
                    "rettype": "abstract",
                },
            )
            fetch_resp.raise_for_status()

            # Check for retraction in the XML
            xml_text = fetch_resp.text
            is_retracted = "RetractionIn" in xml_text or "retracted" in xml_text.lower()

            return {
                "matched": True,
                "pmid": id_list[0],
                "is_retracted": is_retracted,
                "xml_snippet": xml_text[:500],
            }

    except Exception as exc:
        logger.warning("PubMed lookup failed for '%s': %s", title[:60], exc)
        return {"matched": False, "error": str(exc)}


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="citation_checker.extract_citations")
@traced_node("citation_checker", "extract_citations")
async def extract_citations_node(state: CitationCheckerState) -> dict:
    """Parse the document and extract all AMA-formatted citations."""
    try:
        prompt = EXTRACTION_PROMPT.format(document_text=state.get("document_text", ""))
        result = await llm.generate(
            system=SYSTEM_PROMPT,
            prompt=prompt,
            metadata={"node": "extract_citations"},
        )

        content = result["content"].strip()
        # Strip markdown fencing if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        citations = json.loads(content)
        if not isinstance(citations, list):
            citations = [citations]

        return {
            "extracted_citations": citations,
            "model_used": "claude-sonnet-4-20250514",
            "total_tokens": result["total_tokens"],
            "total_cost": result["cost"],
        }

    except json.JSONDecodeError as e:
        return {
            "errors": state.get("errors", []) + [f"Failed to parse extracted citations: {e}"],
            "extracted_citations": [],
            "retry_count": state.get("retry_count", 0) + 1,
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [f"Citation extraction failed: {e}"],
            "extracted_citations": [],
            "retry_count": state.get("retry_count", 0) + 1,
        }


@traceable(name="citation_checker.lookup_sources")
@traced_node("citation_checker", "lookup_sources")
async def lookup_sources_node(state: CitationCheckerState) -> dict:
    """Look each citation up in PubMed to verify it exists."""
    citations = state.get("extracted_citations", [])
    if not citations:
        return {"lookup_results": []}

    lookup_results = []
    for cit in citations:
        title = cit.get("title", "")
        authors = cit.get("authors", "")
        journal = cit.get("journal", "")

        pubmed_result = await lookup_pubmed(title, authors, journal)
        lookup_results.append({
            **cit,
            "pubmed_match": pubmed_result.get("matched", False),
            "pubmed_pmid": pubmed_result.get("pmid"),
            "pubmed_retracted": pubmed_result.get("is_retracted", False),
            "lookup_error": pubmed_result.get("error"),
        })

    return {"lookup_results": lookup_results}


@traceable(name="citation_checker.verify_and_score")
@traced_node("citation_checker", "verify_and_score")
async def verify_and_score_node(state: CitationCheckerState) -> dict:
    """Check retraction status, freshness, and score each citation."""
    lookup_results = state.get("lookup_results", [])
    if not lookup_results:
        return {
            "citation_results": [],
            "trust_score": 0.0,
            "errors": state.get("errors", []) + ["No citations to verify"],
        }

    current_year = datetime.now().year
    cutoff_year = current_year - FRESHNESS_YEARS

    try:
        prompt = VERIFICATION_PROMPT.format(
            current_year=current_year,
            cutoff_year=cutoff_year,
            disease_state=state.get("disease_state", "not specified"),
            lookup_json=json.dumps(lookup_results, indent=2, default=str),
        )
        result = await llm.generate(
            system=SYSTEM_PROMPT,
            prompt=prompt,
            metadata={"node": "verify_and_score"},
        )

        content = result["content"].strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        citation_results = json.loads(content)
        if not isinstance(citation_results, list):
            citation_results = [citation_results]

        # Calculate trust score
        total = len(citation_results)
        if total == 0:
            trust_score = 0.0
        else:
            verified_count = sum(
                1 for c in citation_results
                if c.get("verification_status") in ("verified", "landmark")
            )
            trust_score = verified_count / total

        return {
            "citation_results": citation_results,
            "trust_score": trust_score,
            "total_tokens": state.get("total_tokens", 0) + result["total_tokens"],
            "total_cost": state.get("total_cost", 0.0) + result["cost"],
        }

    except json.JSONDecodeError as e:
        return {
            "errors": state.get("errors", []) + [f"Failed to parse verification results: {e}"],
            "citation_results": [],
            "trust_score": 0.0,
            "retry_count": state.get("retry_count", 0) + 1,
        }
    except Exception as e:
        return {
            "errors": state.get("errors", []) + [f"Verification failed: {e}"],
            "citation_results": [],
            "trust_score": 0.0,
            "retry_count": state.get("retry_count", 0) + 1,
        }


@traceable(name="citation_checker.write_summary")
@traced_node("citation_checker", "write_summary")
async def write_summary_node(state: CitationCheckerState) -> dict:
    """Write the executive summary."""
    citation_results = state.get("citation_results", [])
    trust_score = state.get("trust_score", 0.0)

    if not citation_results:
        return {"executive_summary": "No citations found in the document."}

    try:
        prompt = SUMMARY_PROMPT.format(
            trust_score=trust_score,
            results_json=json.dumps(citation_results, indent=2, default=str),
        )
        result = await llm.generate(
            system=SYSTEM_PROMPT,
            prompt=prompt,
            metadata={"node": "write_summary"},
        )

        return {
            "executive_summary": result["content"].strip(),
            "total_tokens": state.get("total_tokens", 0) + result["total_tokens"],
            "total_cost": state.get("total_cost", 0.0) + result["cost"],
        }

    except Exception as e:
        # Summary is non-critical — generate a fallback
        total = len(citation_results)
        verified = sum(1 for c in citation_results if c.get("verification_status") == "verified")
        retracted = sum(1 for c in citation_results if c.get("verification_status") == "retracted")
        not_found = sum(1 for c in citation_results if c.get("verification_status") == "not_found")
        outdated = sum(1 for c in citation_results if c.get("verification_status") == "outdated")
        landmark = sum(1 for c in citation_results if c.get("verification_status") == "landmark")

        fallback = (
            f"{total} citations checked. {verified} verified, {landmark} landmark, "
            f"{not_found} not found, {retracted} retracted, {outdated} outdated. "
            f"Overall trust score: {trust_score:.0%}."
        )
        return {
            "executive_summary": fallback,
            "errors": state.get("errors", []) + [f"Summary generation failed, using fallback: {e}"],
        }


@traceable(name="citation_checker.validate_quality")
@traced_node("citation_checker", "validate_quality")
async def validate_quality_node(state: CitationCheckerState) -> dict:
    """Quality gate — verify the results are complete and consistent."""
    citation_results = state.get("citation_results", [])
    extracted = state.get("extracted_citations", [])
    issues = []

    # Check all extracted citations were processed
    if len(citation_results) < len(extracted):
        issues.append(
            f"Only {len(citation_results)}/{len(extracted)} citations were verified"
        )

    # Check every result has a status
    missing_status = [
        c.get("raw_citation", "?")[:40]
        for c in citation_results
        if not c.get("verification_status")
    ]
    if missing_status:
        issues.append(f"{len(missing_status)} citations missing verification status")

    # Check every result has a confidence score
    missing_confidence = [
        c for c in citation_results
        if c.get("confidence") is None
    ]
    if missing_confidence:
        issues.append(f"{len(missing_confidence)} citations missing confidence score")

    # Check trust score is reasonable
    trust_score = state.get("trust_score", 0.0)
    if citation_results and trust_score == 0.0:
        verified_any = any(
            c.get("verification_status") in ("verified", "landmark")
            for c in citation_results
        )
        if verified_any:
            issues.append("Trust score is 0 but some citations are verified — scoring error")

    quality_passed = len(issues) == 0
    quality_score = 1.0 if quality_passed else max(0.0, 1.0 - (len(issues) * 0.25))

    result = {"quality_score": quality_passed}
    if issues:
        result["errors"] = state.get("errors", []) + issues
        result["retry_count"] = state.get("retry_count", 0) + 1

    return result


@traceable(name="citation_checker.prepare_registry_request")
@traced_node("citation_checker", "prepare_registry_request")
async def prepare_registry_request_node(state: CitationCheckerState) -> dict:
    """Build a registry_request payload for the Registry Agent to persist citations."""
    citation_results = state.get("citation_results", [])
    project_id = state.get("project_id")

    if not project_id or not citation_results:
        return {"registry_request": {}}

    verified_citations = [
        {
            "ref_type": "pubmed" if c.get("pmid") else "doi",
            "ref_id": str(c.get("pmid") or c.get("doi") or ""),
            "title": c.get("title", "Untitled"),
            "authors": c.get("authors", ""),
            "journal": c.get("journal", ""),
            "url": c.get("doi", ""),
            "abstract": "",
            "cached_content": c,
            "verification_status": c.get("verification_status", "verified"),
            "verified_by": "citation_checker_agent",
        }
        for c in citation_results
        if c.get("verification_status") in ("verified", "landmark")
        and (c.get("pmid") or c.get("doi"))
    ]

    if not verified_citations:
        return {"registry_request": {}}

    return {
        "registry_request": {
            "action": "save_citations",
            "project_id": project_id,
            "payload": {"citations": verified_citations},
        }
    }


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def should_retry(state: CitationCheckerState) -> str:
    """Conditional edge: retry if quality check failed and retries remain."""
    if state.get("quality_score") is True:
        return "done"
    retry_count = state.get("retry_count", 0)
    if retry_count < MAX_RETRIES:
        return "retry"
    return "done"  # Max retries hit — proceed with what we have


# =============================================================================
# GRAPH ASSEMBLY
# =============================================================================

builder = StateGraph(CitationCheckerState)

# Add nodes
builder.add_node("extract_citations", extract_citations_node)
builder.add_node("lookup_sources", lookup_sources_node)
builder.add_node("verify_and_score", verify_and_score_node)
builder.add_node("write_summary", write_summary_node)
builder.add_node("validate_quality", validate_quality_node)
builder.add_node("prepare_registry_request", prepare_registry_request_node)

# Linear flow through processing
builder.set_entry_point("extract_citations")
builder.add_edge("extract_citations", "lookup_sources")
builder.add_edge("lookup_sources", "verify_and_score")
builder.add_edge("verify_and_score", "write_summary")
builder.add_edge("write_summary", "validate_quality")

# Quality gate — retry or prepare for registry
builder.add_conditional_edges(
    "validate_quality",
    should_retry,
    {
        "done": "prepare_registry_request",
        "retry": "extract_citations",
    },
)

# Prepare registry request then done
builder.add_edge("prepare_registry_request", END)


# =============================================================================
# EXPORT (required for LangGraph Cloud)
# =============================================================================

graph = builder.compile()
