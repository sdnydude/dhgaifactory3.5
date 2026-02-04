"""
Research Agent - Agent #2
=========================
Literature review, epidemiology, and market intelligence for CME grants.

LangGraph Cloud Ready:
- Produces structured research report with 30+ citations
- Covers epidemiology, treatment landscape, guidelines, market context
- Output feeds Gap Analysis Agent and all downstream agents
"""

import os
import re
import json
import operator
import httpx
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


# =============================================================================
# CONFIGURATION
# =============================================================================

THERAPEUTIC_AREAS = [
    "cardiology", "oncology", "neurology", "pulmonology", "gastroenterology",
    "endocrinology", "rheumatology", "infectious_disease", "dermatology",
    "psychiatry", "nephrology", "hematology", "immunology", "primary_care"
]


class EvidenceLevel(str, Enum):
    """Oxford Centre for Evidence-Based Medicine Levels"""
    LEVEL_1A = "systematic_review_meta_analysis"
    LEVEL_1B = "high_quality_rct"
    LEVEL_2A = "lower_quality_rct"
    LEVEL_2B = "cohort_case_control"
    LEVEL_3 = "case_series"
    LEVEL_4 = "expert_opinion"
    LEVEL_5 = "narrative_review"


# =============================================================================
# STATE DEFINITION
# =============================================================================

class ResearchState(TypedDict):
    # === INPUT (from intake form) ===
    therapeutic_area: str
    disease_state: str
    target_audience: str
    geographic_focus: str
    supporter_company: Optional[str]
    supporter_products: Optional[List[str]]
    known_gaps: Optional[List[str]]
    competitor_products: Optional[List[str]]
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    
    # Research results by section
    epidemiology_data: Dict[str, Any]
    economic_burden_data: Dict[str, Any]
    treatment_landscape_data: Dict[str, Any]
    guidelines_data: Dict[str, Any]
    market_intelligence_data: Dict[str, Any]
    literature_synthesis_data: Dict[str, Any]
    
    # Citations
    citations: List[Dict[str, Any]]
    
    # === OUTPUT ===
    research_report: Dict[str, Any]
    research_document: str  # Rendered prose document
    
    # Metadata
    search_queries_executed: int
    sources_reviewed: int
    sources_cited: int
    errors: List[str]
    model_used: str
    total_tokens: int
    total_cost: float



# =============================================================================
# LLM CLIENT
# =============================================================================

class LLMClient:
    """Claude-based LLM client for research synthesis."""
    
    def __init__(self):
        self.model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=8192
        )
        self.cost_per_1k_input = 0.003
        self.cost_per_1k_output = 0.015
    
    @traceable(name="research_llm_call", run_type="llm")
    async def generate(self, system: str, prompt: str, metadata: dict = None) -> dict:
        """Generate response with cost tracking."""
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=prompt)
        ]
        
        response = await self.model.ainvoke(
            messages,
            config={"metadata": metadata or {}}
        )
        
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = response.usage_metadata.get("input_tokens", 0)
            output_tokens = response.usage_metadata.get("output_tokens", 0)
        
        cost = (input_tokens / 1000 * self.cost_per_1k_input) + (output_tokens / 1000 * self.cost_per_1k_output)
        
        return {
            "content": response.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost
        }


llm = LLMClient()


# =============================================================================
# PUBMED CLIENT
# =============================================================================

class PubMedClient:
    """PubMed E-Utils API client."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    @traceable(name="pubmed_search", run_type="retriever")
    async def search(self, query: str, max_results: int = 50, years: int = 5) -> List[str]:
        """Search PubMed and return PMIDs."""
        min_date = f"{datetime.now().year - years}/01/01"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "mindate": min_date,
            "datetype": "pdat",
            "retmode": "json",
            "sort": "relevance"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("esearchresult", {}).get("idlist", [])
    
    @traceable(name="pubmed_fetch", run_type="retriever")
    async def fetch_details(self, pmids: List[str]) -> List[Dict]:
        """Fetch article details for PMIDs."""
        if not pmids:
            return []
        
        params = {
            "db": "pubmed",
            "id": ",".join(pmids[:50]),
            "retmode": "xml"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
            response.raise_for_status()
            return self._parse_xml(response.text)
    
    def _parse_xml(self, xml_text: str) -> List[Dict]:
        """Parse PubMed XML response."""
        import xml.etree.ElementTree as ET
        articles = []
        
        try:
            root = ET.fromstring(xml_text)
            for article in root.findall(".//PubmedArticle"):
                try:
                    medline = article.find(".//MedlineCitation")
                    if medline is None:
                        continue
                    
                    pmid = medline.findtext("PMID", "")
                    art = medline.find(".//Article")
                    if art is None:
                        continue
                    
                    title = art.findtext(".//ArticleTitle", "")
                    abstract_parts = [el.text or "" for el in art.findall(".//AbstractText")]
                    abstract = " ".join(abstract_parts)
                    
                    journal_el = art.find(".//Journal")
                    journal = journal_el.findtext(".//Title", "") if journal_el else ""
                    
                    year = ""
                    pub_date = journal_el.find(".//PubDate") if journal_el else None
                    if pub_date is not None:
                        year = pub_date.findtext("Year", "")
                    
                    authors = []
                    for author in art.findall(".//Author"):
                        last = author.findtext("LastName", "")
                        init = author.findtext("Initials", "")
                        if last:
                            authors.append(f"{last} {init}".strip())
                    
                    doi = ""
                    for eid in article.findall(".//ArticleId"):
                        if eid.get("IdType") == "doi":
                            doi = eid.text or ""
                            break
                    
                    pub_types = [pt.text for pt in medline.findall(".//PublicationType") if pt.text]
                    
                    articles.append({
                        "pmid": pmid,
                        "doi": doi,
                        "title": title,
                        "authors": authors[:5],
                        "journal": journal,
                        "year": int(year) if year.isdigit() else 0,
                        "abstract": abstract[:1000],
                        "publication_types": pub_types,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    })
                except Exception:
                    continue
        except Exception:
            pass
        
        return articles


# =============================================================================
# PERPLEXITY CLIENT
# =============================================================================

class PerplexityClient:
    """Perplexity API for academic search."""
    
    ACADEMIC_DOMAINS = [
        "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "cochranelibrary.com",
        "jamanetwork.com", "nejm.org", "thelancet.com", "bmj.com",
        "nature.com", "sciencedirect.com", "nih.gov", "cdc.gov", "fda.gov"
    ]
    
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
    
    @traceable(name="perplexity_search", run_type="retriever")
    async def search(self, query: str, focus: str = "academic") -> dict:
        """Search Perplexity with academic focus."""
        if not self.api_key:
            return {"content": "", "citations": []}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """You are a medical research assistant. 
ONLY cite peer-reviewed publications from major medical journals.
Include PMID or DOI for every source.
Focus on recent data (last 5 years preferred).
Include specific statistics and numbers."""
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "return_citations": True,
            "search_domain_filter": self.ACADEMIC_DOMAINS
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return {
                "content": data["choices"][0]["message"]["content"],
                "citations": data.get("citations", [])
            }


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

RESEARCH_SYSTEM_PROMPT = """You are a medical research specialist conducting literature review and market intelligence for continuing medical education grant applications. Your research must be:

1. COMPREHENSIVE: Cover epidemiology, treatment landscape, guidelines, and market context
2. CURRENT: Prioritize sources from the past 3 years; flag older foundational studies
3. AUTHORITATIVE: Prefer peer-reviewed journals, society guidelines, and government data
4. QUANTITATIVE: Include specific numbers, percentages, and statistics throughout
5. BALANCED: Present the full landscape, not just supporter-favorable data

CRITICAL REQUIREMENTS:
- Minimum 30 unique, verifiable citations
- Every statistic must have a citation
- Include publication year for all sources
- Distinguish between US and global data
- Flag any data older than 5 years
- Note conflicting evidence where it exists

OUTPUT FORMAT:
Produce structured research following the exact schema provided. Every section must contain specific, cited data points. Do not use placeholder language like "studies show" without naming the specific study.

PROHIBITED:
- Generic statements without citations
- Unsourced statistics
- Speculation presented as fact
- Promotional language about any product
- Outdated data without flagging"""


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="research_epidemiology_node", run_type="chain")
async def research_epidemiology_node(state: ResearchState) -> dict:
    """Research epidemiology data for the disease state."""
    
    disease = state.get("disease_state", "")
    geographic = state.get("geographic_focus", "United States")
    
    # Search PubMed for epidemiology
    pubmed = PubMedClient()
    pmids = await pubmed.search(f"{disease} epidemiology prevalence incidence", max_results=20, years=5)
    articles = await pubmed.fetch_details(pmids)
    
    # Search Perplexity for current stats
    perplexity = PerplexityClient()
    epi_result = await perplexity.search(
        f"What is the current prevalence, incidence, mortality, and disease burden for {disease} in {geographic}? "
        f"Include specific statistics with citations from CDC, WHO, or peer-reviewed sources."
    )
    
    system = f"""{RESEARCH_SYSTEM_PROMPT}

You are extracting EPIDEMIOLOGY data. Return a JSON object with this exact structure:
{{
    "prevalence": {{
        "global": "string with citation",
        "us": "string with citation",
        "regional_variations": ["list of variations with citations"]
    }},
    "incidence": {{
        "annual_new_cases": "string with citation",
        "trends": "string with citation"
    }},
    "demographics": {{
        "age_distribution": "string with citation",
        "sex_distribution": "string with citation",
        "racial_ethnic_factors": "string with citation"
    }},
    "burden": {{
        "mortality": "string with citation",
        "morbidity": "string with citation",
        "quality_of_life_impact": "string with citation"
    }},
    "projections": {{
        "future_prevalence": "string with citation",
        "drivers_of_change": "string with citation"
    }}
}}"""
    
    # Prepare context from PubMed
    pubmed_context = "\n".join([
        f"- {a['title']} ({a['journal']}, {a['year']}): {a['abstract'][:300]}..."
        for a in articles[:10]
    ])
    
    prompt = f"""Extract epidemiology data for {disease} in {geographic}.

PUBMED ARTICLES:
{pubmed_context}

PERPLEXITY FINDINGS:
{epi_result.get('content', '')}

Return ONLY valid JSON matching the schema above. Every field must have a citation."""

    result = await llm.generate(system, prompt, {"step": "epidemiology"})
    
    try:
        # Extract JSON from response
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            epi_data = json.loads(json_match.group())
        else:
            epi_data = {"error": "Failed to parse epidemiology data"}
    except json.JSONDecodeError:
        epi_data = {"error": "Invalid JSON in epidemiology response"}
    
    # Collect citations from articles
    new_citations = [
        {
            "id": a["pmid"],
            "pmid": a["pmid"],
            "doi": a.get("doi", ""),
            "authors": ", ".join(a["authors"][:3]) + " et al." if len(a["authors"]) > 3 else ", ".join(a["authors"]),
            "title": a["title"],
            "journal": a["journal"],
            "year": a["year"],
            "relevance": "epidemiology",
            "url": a["url"]
        }
        for a in articles if a.get("pmid")
    ]
    
    prev_citations = state.get("citations", [])
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_queries = state.get("search_queries_executed", 0)
    
    return {
        "epidemiology_data": epi_data,
        "citations": prev_citations + new_citations,
        "search_queries_executed": prev_queries + 2,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="research_economic_burden_node", run_type="chain")
async def research_economic_burden_node(state: ResearchState) -> dict:
    """Research economic burden data."""
    
    disease = state.get("disease_state", "")
    
    perplexity = PerplexityClient()
    econ_result = await perplexity.search(
        f"What is the economic burden of {disease}? Include direct healthcare costs, "
        f"indirect costs (productivity, caregiver burden), and healthcare utilization "
        f"(hospitalizations, ED visits) with specific dollar amounts and citations."
    )
    
    system = f"""{RESEARCH_SYSTEM_PROMPT}

You are extracting ECONOMIC BURDEN data. Return a JSON object:
{{
    "direct_costs": {{
        "annual_total": "dollar amount with citation",
        "per_patient": "dollar amount with citation",
        "cost_drivers": ["list of drivers with citations"]
    }},
    "indirect_costs": {{
        "productivity_loss": "dollar amount with citation",
        "caregiver_burden": "description with citation"
    }},
    "healthcare_utilization": {{
        "hospitalizations": "rate or number with citation",
        "ed_visits": "rate or number with citation",
        "outpatient_visits": "rate or number with citation"
    }}
}}"""
    
    prompt = f"""Extract economic burden data for {disease}.

RESEARCH DATA:
{econ_result.get('content', '')}

Return ONLY valid JSON. Every dollar amount must have a citation."""

    result = await llm.generate(system, prompt, {"step": "economic_burden"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            econ_data = json.loads(json_match.group())
        else:
            econ_data = {"error": "Failed to parse economic data"}
    except json.JSONDecodeError:
        econ_data = {"error": "Invalid JSON in economic response"}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_queries = state.get("search_queries_executed", 0)
    
    return {
        "economic_burden_data": econ_data,
        "search_queries_executed": prev_queries + 1,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="research_treatment_landscape_node", run_type="chain")
async def research_treatment_landscape_node(state: ResearchState) -> dict:
    """Research current treatment landscape."""
    
    disease = state.get("disease_state", "")
    
    # Search PubMed for treatment/therapy
    pubmed = PubMedClient()
    pmids = await pubmed.search(f"{disease} treatment therapy guideline", max_results=25, years=3)
    articles = await pubmed.fetch_details(pmids)
    
    perplexity = PerplexityClient()
    tx_result = await perplexity.search(
        f"What are the current treatment options for {disease}? Include guideline-recommended "
        f"first-line and second-line therapies, recent drug approvals, and pipeline agents in Phase 3."
    )
    
    system = f"""{RESEARCH_SYSTEM_PROMPT}

You are extracting TREATMENT LANDSCAPE data. Return a JSON object:
{{
    "current_standards": {{
        "first_line": ["list of treatments with guidelines citation"],
        "second_line": ["list with citations"],
        "emerging": ["list of recent approvals with FDA approval dates"]
    }},
    "guideline_summary": {{
        "major_guidelines": [{{"society": "name", "year": 2024, "key_recs": ["recs"]}}],
        "recent_updates": ["list of updates with dates"],
        "areas_of_consensus": ["list"],
        "areas_of_controversy": ["list"]
    }},
    "pipeline": {{
        "phase_3": ["list of agents in Phase 3"],
        "recently_approved": ["list of drugs approved in last 2 years"]
    }}
}}"""
    
    pubmed_context = "\n".join([
        f"- {a['title']} ({a['journal']}, {a['year']})"
        for a in articles[:15]
    ])
    
    prompt = f"""Extract treatment landscape for {disease}.

PUBMED ARTICLES:
{pubmed_context}

CURRENT DATA:
{tx_result.get('content', '')}

Return ONLY valid JSON. Name specific guidelines (ACC/AHA, ESC, etc.) and drugs."""

    result = await llm.generate(system, prompt, {"step": "treatment_landscape"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            tx_data = json.loads(json_match.group())
        else:
            tx_data = {"error": "Failed to parse treatment data"}
    except json.JSONDecodeError:
        tx_data = {"error": "Invalid JSON in treatment response"}
    
    new_citations = [
        {
            "id": a["pmid"],
            "pmid": a["pmid"],
            "doi": a.get("doi", ""),
            "authors": ", ".join(a["authors"][:3]) + " et al." if len(a["authors"]) > 3 else ", ".join(a["authors"]),
            "title": a["title"],
            "journal": a["journal"],
            "year": a["year"],
            "relevance": "treatment",
            "url": a["url"]
        }
        for a in articles if a.get("pmid")
    ]
    
    prev_citations = state.get("citations", [])
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_queries = state.get("search_queries_executed", 0)
    
    return {
        "treatment_landscape_data": tx_data,
        "citations": prev_citations + new_citations,
        "search_queries_executed": prev_queries + 2,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="research_guidelines_node", run_type="chain")
async def research_guidelines_node(state: ResearchState) -> dict:
    """Research clinical practice guidelines."""
    
    disease = state.get("disease_state", "")
    
    perplexity = PerplexityClient()
    guide_result = await perplexity.search(
        f"What are the major clinical practice guidelines for {disease}? "
        f"Include society names, publication years, and key recommendations. "
        f"Focus on ACC, AHA, ESC, ASCO, NCCN, and other major specialty societies."
    )
    
    system = f"""{RESEARCH_SYSTEM_PROMPT}

You are extracting GUIDELINES data. Return a JSON object:
{{
    "major_guidelines": [
        {{
            "society": "society name (e.g., ACC/AHA)",
            "title": "guideline title",
            "year": 2024,
            "key_recommendations": ["rec 1", "rec 2"],
            "evidence_grades": "description of grading system used"
        }}
    ],
    "recent_updates": [
        {{
            "society": "name",
            "update_type": "focused update or full revision",
            "date": "month year",
            "key_changes": ["change 1", "change 2"]
        }}
    ],
    "consensus_areas": ["list of areas where guidelines agree"],
    "controversy_areas": ["list of areas where guidelines differ"]
}}"""
    
    prompt = f"""Extract guideline information for {disease}.

RESEARCH DATA:
{guide_result.get('content', '')}

Return ONLY valid JSON. Be specific about society names and years."""

    result = await llm.generate(system, prompt, {"step": "guidelines"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            guide_data = json.loads(json_match.group())
        else:
            guide_data = {"error": "Failed to parse guidelines data"}
    except json.JSONDecodeError:
        guide_data = {"error": "Invalid JSON in guidelines response"}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_queries = state.get("search_queries_executed", 0)
    
    return {
        "guidelines_data": guide_data,
        "search_queries_executed": prev_queries + 1,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="research_market_intelligence_node", run_type="chain")
async def research_market_intelligence_node(state: ResearchState) -> dict:
    """Research market intelligence (if supporter context provided)."""
    
    disease = state.get("disease_state", "")
    supporter = state.get("supporter_company", "")
    products = state.get("supporter_products", [])
    competitors = state.get("competitor_products", [])
    
    perplexity = PerplexityClient()
    
    if supporter:
        market_query = (
            f"What is the market landscape for {disease} treatments? "
            f"Include market size, growth trajectory, and key players. "
            f"What is {supporter}'s position in this market?"
        )
    else:
        market_query = (
            f"What is the market landscape for {disease} treatments? "
            f"Include market size, growth trajectory, and major pharmaceutical companies."
        )
    
    market_result = await perplexity.search(market_query)
    
    system = f"""{RESEARCH_SYSTEM_PROMPT}

You are extracting MARKET INTELLIGENCE data. Return a JSON object:
{{
    "market_dynamics": {{
        "market_size": "dollar amount with source",
        "growth_trajectory": "percentage and timeframe",
        "key_players": ["list of major companies"]
    }},
    "supporter_context": {{
        "company_position": "market position description",
        "product_portfolio": ["list of products in this space"],
        "recent_approvals": ["recent FDA approvals with dates"],
        "competitive_positioning": "how they differentiate"
    }},
    "competitive_landscape": {{
        "major_competitors": ["list of competitor products"],
        "market_share": "breakdown if available",
        "pipeline_competition": ["upcoming competitors"]
    }}
}}"""
    
    prompt = f"""Extract market intelligence for {disease}.

SUPPORTER COMPANY: {supporter or 'Not specified'}
SUPPORTER PRODUCTS: {', '.join(products) if products else 'Not specified'}
COMPETITOR PRODUCTS: {', '.join(competitors) if competitors else 'Not specified'}

MARKET DATA:
{market_result.get('content', '')}

Return ONLY valid JSON. Be balanced and include competitive context."""

    result = await llm.generate(system, prompt, {"step": "market_intelligence"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            market_data = json.loads(json_match.group())
        else:
            market_data = {"error": "Failed to parse market data"}
    except json.JSONDecodeError:
        market_data = {"error": "Invalid JSON in market response"}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    prev_queries = state.get("search_queries_executed", 0)
    
    return {
        "market_intelligence_data": market_data,
        "search_queries_executed": prev_queries + 1,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="synthesize_research_node", run_type="chain")
async def synthesize_research_node(state: ResearchState) -> dict:
    """Synthesize all research into literature findings and gaps."""
    
    disease = state.get("disease_state", "")
    epi = state.get("epidemiology_data", {})
    econ = state.get("economic_burden_data", {})
    tx = state.get("treatment_landscape_data", {})
    guidelines = state.get("guidelines_data", {})
    
    system = f"""{RESEARCH_SYSTEM_PROMPT}

You are synthesizing research into KEY FINDINGS and EVIDENCE GAPS. Return a JSON object:
{{
    "key_findings": [
        {{
            "finding": "specific finding with data",
            "source": "citation",
            "clinical_relevance": "why this matters"
        }}
    ],
    "evidence_gaps": [
        "gap 1: what we don't know",
        "gap 2: conflicting evidence on...",
        "gap 3: limited data on..."
    ],
    "research_priorities": [
        "priority 1: most urgent research need",
        "priority 2: important but less urgent"
    ]
}}"""
    
    prompt = f"""Synthesize research on {disease}.

EPIDEMIOLOGY:
{json.dumps(epi, indent=2)[:2000]}

ECONOMIC BURDEN:
{json.dumps(econ, indent=2)[:1000]}

TREATMENT LANDSCAPE:
{json.dumps(tx, indent=2)[:2000]}

GUIDELINES:
{json.dumps(guidelines, indent=2)[:1500]}

Identify 5-10 key findings and 3-5 evidence gaps. Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "synthesis"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            synth_data = json.loads(json_match.group())
        else:
            synth_data = {"key_findings": [], "evidence_gaps": [], "research_priorities": []}
    except json.JSONDecodeError:
        synth_data = {"key_findings": [], "evidence_gaps": [], "research_priorities": []}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "literature_synthesis_data": synth_data,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="assemble_research_report_node", run_type="chain")
async def assemble_research_report_node(state: ResearchState) -> dict:
    """Assemble final research report."""
    
    # Deduplicate citations
    citations = state.get("citations", [])
    seen_ids = set()
    unique_citations = []
    for c in citations:
        cid = c.get("pmid") or c.get("id")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            unique_citations.append(c)
    
    report = {
        "metadata": {
            "agent_version": "2.0",
            "execution_timestamp": datetime.now().isoformat(),
            "search_queries_executed": state.get("search_queries_executed", 0),
            "sources_reviewed": len(citations),
            "sources_cited": len(unique_citations)
        },
        "epidemiology": state.get("epidemiology_data", {}),
        "economic_burden": state.get("economic_burden_data", {}),
        "treatment_landscape": state.get("treatment_landscape_data", {}),
        "guidelines": state.get("guidelines_data", {}),
        "market_intelligence": state.get("market_intelligence_data", {}),
        "literature_synthesis": state.get("literature_synthesis_data", {}),
        "citations": unique_citations
    }
    
    # Quality checks
    citation_count = len(unique_citations)
    meets_citation_minimum = citation_count >= 30
    
    return {
        "research_report": report,
        "sources_reviewed": len(citations),
        "sources_cited": citation_count,
        "messages": [HumanMessage(content=f"Research complete: {citation_count} citations, minimum met: {meets_citation_minimum}")]
    }


@traceable(name="render_research_document_node", run_type="chain")
async def render_research_document_node(state: ResearchState) -> dict:
    """Render the research report as a readable prose document."""
    
    disease = state.get("disease_state", "")
    report = state.get("research_report", {})
    
    system = """You are a medical writer converting structured research data into a cohesive, readable research report.

FORMATTING RULES:
- Use markdown headers (## for main sections)
- Write flowing prose paragraphs, not bullet points
- Include inline citations in format (Author, Journal Year)
- 80%+ prose density
- Active voice
- Specific numbers and data throughout

STRUCTURE:
1. Executive Summary (2-3 paragraphs)
2. Epidemiology and Disease Burden
3. Economic Impact
4. Current Treatment Landscape
5. Clinical Practice Guidelines
6. Market Context (if applicable)
7. Evidence Gaps and Research Priorities
8. References

Do NOT use:
- Em dashes (—)
- "It's important to note"
- "Studies show" without naming the study
- Bullet points in the main text
"""
    
    prompt = f"""Convert this research data on {disease} into a cohesive research document.

RESEARCH DATA:
{json.dumps(report, indent=2)[:12000]}

Write a complete, readable research document following the structure above. Use full sentences and paragraphs. Include all key statistics with their citations inline."""

    result = await llm.generate(system, prompt, {"step": "render_document"})
    
    document = result["content"]
    
    # Add references section from citations
    citations = report.get("citations", [])
    if citations:
        document += "\n\n## References\n\n"
        for i, c in enumerate(citations[:30], 1):
            authors = c.get("authors", "Unknown")
            title = c.get("title", "")
            journal = c.get("journal", "")
            year = c.get("year", "")
            pmid = c.get("pmid", "")
            document += f"{i}. {authors}. {title}. *{journal}*. {year}."
            if pmid:
                document += f" PMID: {pmid}"
            document += "\n\n"
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "research_document": document,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


# =============================================================================
# BUILD GRAPH
# =============================================================================


def create_research_graph() -> StateGraph:
    """Create the Research Agent graph."""
    
    graph = StateGraph(ResearchState)
    
    # Add nodes
    graph.add_node("research_epidemiology", research_epidemiology_node)
    graph.add_node("research_economic_burden", research_economic_burden_node)
    graph.add_node("research_treatment_landscape", research_treatment_landscape_node)
    graph.add_node("research_guidelines", research_guidelines_node)
    graph.add_node("research_market_intelligence", research_market_intelligence_node)
    graph.add_node("synthesize_research", synthesize_research_node)
    graph.add_node("assemble_report", assemble_research_report_node)
    graph.add_node("render_document", render_research_document_node)
    
    # Flow: research -> synthesis -> assembly -> render
    graph.set_entry_point("research_epidemiology")
    
    # Sequential for now (can be parallelized later)
    graph.add_edge("research_epidemiology", "research_economic_burden")
    graph.add_edge("research_economic_burden", "research_treatment_landscape")
    graph.add_edge("research_treatment_landscape", "research_guidelines")
    graph.add_edge("research_guidelines", "research_market_intelligence")
    graph.add_edge("research_market_intelligence", "synthesize_research")
    graph.add_edge("synthesize_research", "assemble_report")
    graph.add_edge("assemble_report", "render_document")
    graph.add_edge("render_document", END)
    
    return graph



# Compile the graph for LangGraph Cloud
graph = create_research_graph().compile()


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        test_state = {
            "therapeutic_area": "cardiology",
            "disease_state": "heart failure with preserved ejection fraction",
            "target_audience": "cardiologists",
            "geographic_focus": "United States",
            "supporter_company": "",
            "supporter_products": [],
            "known_gaps": [],
            "competitor_products": [],
            "messages": [],
            "citations": [],
            "errors": [],
            "search_queries_executed": 0,
            "total_tokens": 0,
            "total_cost": 0.0
        }
        
        result = await graph.ainvoke(test_state)
        
        print(f"\n=== RESEARCH REPORT ===")
        print(f"Citations: {result.get('sources_cited', 0)} (target: 30+)")
        print(f"Queries executed: {result.get('search_queries_executed', 0)}")
        print(f"Total tokens: {result.get('total_tokens', 0)}")
        print(f"Total cost: ${result.get('total_cost', 0):.4f}")
        
        report = result.get("research_report", {})
        print(f"\n=== SECTIONS ===")
        for section in ["epidemiology", "economic_burden", "treatment_landscape", "guidelines", "market_intelligence"]:
            data = report.get(section, {})
            print(f"- {section}: {'✓' if data and 'error' not in data else '✗'}")
    
    asyncio.run(test())
