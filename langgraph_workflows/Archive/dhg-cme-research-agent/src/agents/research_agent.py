"""
DHG CME Research Agent
======================
Evidence-based research agent for clinical gap analysis, needs assessments,
and CME content development.

CRITICAL: Only uses peer-reviewed, evidence-based sources.
Integrates: PubMed, Perplexity Academic, with LLM synthesis via Claude/Gemini.

LangSmith Cloud: Full tracing and observability enabled.

Author: Digital Harmony Group
Version: 1.1.0
"""

import os
import json
import asyncio
from datetime import datetime
from typing import TypedDict, Annotated, Literal, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

# LangSmith Cloud integration
from langsmith import Client, traceable
from langsmith.run_helpers import get_current_run_tree
import langsmith

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# LangChain for LangSmith-native tracing
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# Direct LLM clients (fallback)
import anthropic
import google.generativeai as genai

# HTTP for API calls
import httpx

# =============================================================================
# LANGSMITH CONFIGURATION
# =============================================================================

# Initialize LangSmith client
langsmith_client = Client()

# Configure LangSmith tracing
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "dhg-cme-research-agent")

def get_langsmith_config():
    """Get LangSmith run configuration"""
    return {
        "project_name": os.getenv("LANGCHAIN_PROJECT", "dhg-cme-research-agent"),
        "metadata": {
            "agent_version": "1.1.0",
            "division": "DHG CME",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    }

# ============================================================================
# CONFIGURATION
# ============================================================================

class EvidenceLevel(Enum):
    """Oxford Centre for Evidence-Based Medicine Levels"""
    LEVEL_1A = "systematic_review_meta_analysis"
    LEVEL_1B = "high_quality_rct"
    LEVEL_2A = "lower_quality_rct"
    LEVEL_2B = "cohort_case_control"
    LEVEL_3 = "case_series"
    LEVEL_4 = "expert_opinion"
    LEVEL_5 = "narrative_review"  # Flagged, not primary evidence


class SourceType(Enum):
    """Allowed source types for CME content"""
    PUBMED = "pubmed"
    COCHRANE = "cochrane"
    CLINICAL_TRIALS = "clinicaltrials_gov"
    FDA = "fda_labels"
    PRACTICE_GUIDELINE = "practice_guideline"
    PERPLEXITY_ACADEMIC = "perplexity_academic"
    # BLOCKED
    GENERAL_WEB = "general_web"  # Never use


# Therapeutic areas supported
THERAPEUTIC_AREAS = [
    "cardiology", "oncology", "neurology", "pulmonology", "gastroenterology",
    "endocrinology", "rheumatology", "infectious_disease", "dermatology",
    "psychiatry", "nephrology", "hematology", "immunology", "primary_care",
    "pediatrics", "geriatrics", "emergency_medicine", "critical_care"
]

# Model routing configuration
MODEL_CONFIG = {
    "complex_synthesis": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "use_case": "Gap analysis, clinical reasoning, final CME content"
    },
    "bulk_screening": {
        "provider": "google",
        "model": "gemini-2.5-flash-preview-05-20",
        "max_tokens": 4096,
        "use_case": "Literature screening, classification, bulk processing"
    },
    "citation_extraction": {
        "provider": "anthropic",
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 2048,
        "use_case": "Structured extraction, citation parsing"
    },
    "cost_optimized": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "use_case": "Mid-tier tasks, moderate complexity"
    }
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Citation:
    """Structured citation for CME compliance"""
    pmid: Optional[str] = None
    doi: Optional[str] = None
    title: str = ""
    authors: List[str] = field(default_factory=list)
    journal: str = ""
    year: int = 0
    volume: str = ""
    issue: str = ""
    pages: str = ""
    abstract: str = ""
    evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_5
    source_type: SourceType = SourceType.PUBMED
    url: str = ""
    accessed_date: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_ama_format(self) -> str:
        """Format citation in AMA style (standard for medical education)"""
        author_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            author_str += ", et al"
        return f"{author_str}. {self.title}. {self.journal}. {self.year};{self.volume}({self.issue}):{self.pages}."
    
    def to_dict(self) -> dict:
        return {
            "pmid": self.pmid,
            "doi": self.doi,
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "year": self.year,
            "evidence_level": self.evidence_level.value,
            "source_type": self.source_type.value,
            "url": self.url,
            "ama_citation": self.to_ama_format()
        }


@dataclass
class ResearchQuery:
    """Structured research query"""
    topic: str
    therapeutic_area: str
    query_type: Literal["gap_analysis", "needs_assessment", "literature_review", "podcast_content", "cme_content"]
    target_audience: Literal["primary_care", "specialist", "np_pa", "pharmacist", "nurse", "mixed"]
    date_range_years: int = 5  # Default to last 5 years
    minimum_evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_2B
    max_results: int = 50
    include_guidelines: bool = True
    specific_questions: List[str] = field(default_factory=list)


@dataclass
class ResearchResult:
    """Complete research result with evidence trail"""
    query: ResearchQuery
    citations: List[Citation] = field(default_factory=list)
    synthesis: str = ""
    clinical_gaps: List[str] = field(default_factory=list)
    key_findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    evidence_summary: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# STATE DEFINITION FOR LANGGRAPH
# ============================================================================

class AgentState(TypedDict):
    """State passed between nodes in the research graph"""
    # Input
    query: ResearchQuery
    
    # Processing
    messages: Annotated[list, add_messages]
    pubmed_results: List[dict]
    perplexity_results: List[dict]
    validated_citations: List[Citation]
    
    # Output
    synthesis: str
    clinical_gaps: List[str]
    key_findings: List[str]
    final_result: Optional[ResearchResult]
    
    # Control
    current_step: str
    errors: List[str]
    model_used: str
    tokens_used: int
    cost_estimate: float


# ============================================================================
# PUBMED INTEGRATION (E-Utilities API) with LangSmith tracing
# ============================================================================

class PubMedClient:
    """
    PubMed E-Utilities API client.
    
    Uses NCBI's free E-Utilities API.
    Rate limit: 3 requests/second without API key, 10 with key.
    
    Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25500/
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, api_key: Optional[str] = None, email: str = "research@digitalharmonygroup.com"):
        self.api_key = api_key or os.getenv("NCBI_API_KEY")
        self.email = email
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @traceable(name="pubmed_search", run_type="retriever")
    async def search(
        self,
        query: str,
        max_results: int = 50,
        date_range_years: int = 5,
        article_types: Optional[List[str]] = None
    ) -> List[str]:
        """
        Search PubMed and return PMIDs.
        
        Args:
            query: Search terms
            max_results: Maximum number of results
            date_range_years: Limit to recent N years
            article_types: Filter by article type (e.g., "Review", "Clinical Trial")
        
        Returns:
            List of PMIDs
        """
        # Build query with filters
        search_query = query
        
        # Add date filter
        if date_range_years:
            search_query += f" AND ({date_range_years}y[dp])"
        
        # Add article type filters for evidence quality
        if article_types:
            type_filter = " OR ".join([f'"{t}"[pt]' for t in article_types])
            search_query += f" AND ({type_filter})"
        
        params = {
            "db": "pubmed",
            "term": search_query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
            "email": self.email
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        response = await self.client.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
        response.raise_for_status()
        
        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])
    
    @traceable(name="pubmed_fetch_details", run_type="retriever")
    async def fetch_details(self, pmids: List[str]) -> List[dict]:
        """
        Fetch detailed article information for PMIDs.
        
        Returns structured article data including abstract.
        """
        if not pmids:
            return []
        
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": self.email
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        response = await self.client.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
        response.raise_for_status()
        
        # Parse XML response
        return self._parse_pubmed_xml(response.text)
    
    def _parse_pubmed_xml(self, xml_text: str) -> List[dict]:
        """Parse PubMed XML response into structured data"""
        import xml.etree.ElementTree as ET
        
        articles = []
        root = ET.fromstring(xml_text)
        
        for article in root.findall(".//PubmedArticle"):
            try:
                medline = article.find(".//MedlineCitation")
                article_data = medline.find(".//Article")
                
                # Extract PMID
                pmid = medline.find(".//PMID").text
                
                # Extract title
                title_elem = article_data.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else ""
                
                # Extract authors
                authors = []
                for author in article_data.findall(".//Author"):
                    lastname = author.find("LastName")
                    forename = author.find("ForeName")
                    if lastname is not None:
                        name = lastname.text
                        if forename is not None:
                            name = f"{lastname.text} {forename.text[0]}"
                        authors.append(name)
                
                # Extract journal info
                journal = article_data.find(".//Journal")
                journal_title = journal.find(".//Title").text if journal.find(".//Title") is not None else ""
                
                # Extract date
                pub_date = journal.find(".//PubDate")
                year = pub_date.find("Year").text if pub_date.find("Year") is not None else ""
                
                # Extract abstract
                abstract_elem = article_data.find(".//Abstract/AbstractText")
                abstract = abstract_elem.text if abstract_elem is not None else ""
                
                # Extract publication type for evidence grading
                pub_types = [pt.text for pt in medline.findall(".//PublicationType")]
                
                # Extract DOI
                doi = ""
                for id_elem in article.findall(".//ArticleId"):
                    if id_elem.get("IdType") == "doi":
                        doi = id_elem.text
                        break
                
                articles.append({
                    "pmid": pmid,
                    "doi": doi,
                    "title": title,
                    "authors": authors,
                    "journal": journal_title,
                    "year": int(year) if year.isdigit() else 0,
                    "abstract": abstract,
                    "publication_types": pub_types,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })
                
            except Exception as e:
                continue  # Skip malformed articles
        
        return articles
    
    async def close(self):
        await self.client.aclose()


# ============================================================================
# PERPLEXITY INTEGRATION (Academic Mode) with LangSmith tracing
# ============================================================================

class PerplexityClient:
    """
    Perplexity API client with academic/citation focus.
    
    Uses sonar models with citation tracking.
    """
    
    BASE_URL = "https://api.perplexity.ai"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.client = httpx.AsyncClient(timeout=60.0)
    
    @traceable(name="perplexity_academic_search", run_type="retriever")
    async def search(
        self,
        query: str,
        focus: str = "academic",
        return_citations: bool = True
    ) -> dict:
        """
        Search using Perplexity with academic focus.
        
        Args:
            query: Research query
            focus: Search focus ('academic' for peer-reviewed sources)
            return_citations: Include source citations
        
        Returns:
            Dict with response and citations
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Use sonar-pro for better citation quality
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a medical research assistant. ONLY cite peer-reviewed "
                        "publications from PubMed, medical journals, and clinical guidelines. "
                        "NEVER cite general websites, news articles, or non-peer-reviewed sources. "
                        "Always include PMID or DOI when available."
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "return_citations": return_citations,
            "search_domain_filter": [
                "pubmed.ncbi.nlm.nih.gov",
                "ncbi.nlm.nih.gov",
                "cochranelibrary.com",
                "jamanetwork.com",
                "nejm.org",
                "thelancet.com",
                "bmj.com",
                "nature.com",
                "sciencedirect.com",
                "springer.com",
                "wiley.com",
                "nih.gov",
                "cdc.gov",
                "who.int",
                "fda.gov"
            ]
        }
        
        response = await self.client.post(
            f"{self.BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "content": data["choices"][0]["message"]["content"],
            "citations": data.get("citations", []),
            "usage": data.get("usage", {})
        }
    
    async def close(self):
        await self.client.aclose()


# ============================================================================
# EVIDENCE GRADER
# ============================================================================

class EvidenceGrader:
    """
    Grades evidence level based on publication type and study design.
    
    Uses Oxford Centre for Evidence-Based Medicine (OCEBM) levels.
    """
    
    # Mapping of PubMed publication types to evidence levels
    PUBTYPE_MAPPING = {
        # Level 1a
        "Systematic Review": EvidenceLevel.LEVEL_1A,
        "Meta-Analysis": EvidenceLevel.LEVEL_1A,
        
        # Level 1b
        "Randomized Controlled Trial": EvidenceLevel.LEVEL_1B,
        
        # Level 2a/2b
        "Clinical Trial": EvidenceLevel.LEVEL_2A,
        "Controlled Clinical Trial": EvidenceLevel.LEVEL_2A,
        "Cohort Study": EvidenceLevel.LEVEL_2B,
        "Comparative Study": EvidenceLevel.LEVEL_2B,
        
        # Level 3
        "Case Reports": EvidenceLevel.LEVEL_3,
        
        # Level 4
        "Practice Guideline": EvidenceLevel.LEVEL_4,
        "Guideline": EvidenceLevel.LEVEL_4,
        "Consensus Development Conference": EvidenceLevel.LEVEL_4,
        
        # Level 5
        "Review": EvidenceLevel.LEVEL_5,
        "Editorial": EvidenceLevel.LEVEL_5,
        "Comment": EvidenceLevel.LEVEL_5,
        "Letter": EvidenceLevel.LEVEL_5,
    }
    
    @classmethod
    def grade(cls, publication_types: List[str]) -> EvidenceLevel:
        """
        Assign evidence level based on publication types.
        Returns highest (best) evidence level found.
        """
        best_level = EvidenceLevel.LEVEL_5
        
        for pub_type in publication_types:
            if pub_type in cls.PUBTYPE_MAPPING:
                level = cls.PUBTYPE_MAPPING[pub_type]
                # Lower enum value = better evidence
                if list(EvidenceLevel).index(level) < list(EvidenceLevel).index(best_level):
                    best_level = level
        
        return best_level
    
    @classmethod
    def filter_by_minimum_level(
        cls,
        articles: List[dict],
        minimum_level: EvidenceLevel
    ) -> List[dict]:
        """Filter articles to include only those meeting minimum evidence threshold"""
        filtered = []
        min_index = list(EvidenceLevel).index(minimum_level)
        
        for article in articles:
            pub_types = article.get("publication_types", [])
            level = cls.grade(pub_types)
            level_index = list(EvidenceLevel).index(level)
            
            if level_index <= min_index:
                article["evidence_level"] = level
                filtered.append(article)
        
        return filtered


# ============================================================================
# SOURCE VALIDATOR
# ============================================================================

class SourceValidator:
    """
    Validates that sources are peer-reviewed and appropriate for CME.
    
    CRITICAL: Rejects any non-peer-reviewed sources.
    """
    
    # Trusted domains for medical literature
    TRUSTED_DOMAINS = {
        "pubmed.ncbi.nlm.nih.gov",
        "ncbi.nlm.nih.gov",
        "cochranelibrary.com",
        "jamanetwork.com",
        "nejm.org",
        "thelancet.com",
        "bmj.com",
        "nature.com/nm",  # Nature Medicine
        "annals.org",
        "ahajournals.org",
        "diabetesjournals.org",
        "thorax.bmj.com",
        "gut.bmj.com",
        "nih.gov",
        "cdc.gov",
        "who.int",
        "fda.gov",
        "clinicaltrials.gov"
    }
    
    # Blocked sources (never use for CME)
    BLOCKED_DOMAINS = {
        "wikipedia.org",
        "webmd.com",
        "mayoclinic.org",  # Patient-facing, not peer-reviewed
        "healthline.com",
        "medicalnewstoday.com",
        "verywellhealth.com",
        "drugs.com",
        "rxlist.com",
        "medscape.com",  # News, not peer-reviewed
        "everydayhealth.com",
        "reddit.com",
        "quora.com"
    }
    
    @classmethod
    def is_valid_source(cls, url: str) -> bool:
        """Check if URL is from a trusted peer-reviewed source"""
        from urllib.parse import urlparse
        
        try:
            domain = urlparse(url).netloc.lower()
            
            # Check blocked list first
            for blocked in cls.BLOCKED_DOMAINS:
                if blocked in domain:
                    return False
            
            # Check trusted list
            for trusted in cls.TRUSTED_DOMAINS:
                if trusted in domain:
                    return True
            
            # If not in trusted list, reject
            return False
            
        except Exception:
            return False
    
    @classmethod
    def validate_citation(cls, citation: dict) -> tuple[bool, str]:
        """
        Validate a citation for CME use.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        # Must have PMID or DOI
        if not citation.get("pmid") and not citation.get("doi"):
            return False, "No PMID or DOI - cannot verify peer review status"
        
        # Must have valid URL if present
        if citation.get("url") and not cls.is_valid_source(citation["url"]):
            return False, f"Source not from trusted peer-reviewed domain: {citation.get('url')}"
        
        # Must have publication year
        if not citation.get("year") or citation.get("year", 0) < 1900:
            return False, "Invalid or missing publication year"
        
        # Must have title
        if not citation.get("title"):
            return False, "Missing article title"
        
        return True, "Valid peer-reviewed source"


# ============================================================================
# LLM ROUTER (with LangSmith tracing)
# ============================================================================

class LLMRouter:
    """
    Routes requests to appropriate LLM based on task complexity and cost.
    
    Uses LangChain wrappers for native LangSmith Cloud tracing.
    """
    
    def __init__(self):
        # LangChain wrappers with automatic LangSmith tracing
        self.claude_sonnet = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=8192
        )
        
        self.claude_haiku = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=2048
        )
        
        self.gemini_flash = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            max_output_tokens=4096
        )
        
        # Model mapping
        self.models = {
            "complex_synthesis": self.claude_sonnet,
            "bulk_screening": self.gemini_flash,
            "citation_extraction": self.claude_haiku,
            "cost_optimized": self.claude_sonnet
        }
    
    @traceable(name="llm_route_and_execute", run_type="llm")
    async def route_and_execute(
        self,
        task_type: Literal["complex_synthesis", "bulk_screening", "citation_extraction", "cost_optimized"],
        prompt: str,
        system_prompt: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Route to appropriate model and execute with LangSmith tracing.
        
        Returns:
            Dict with response, model_used, tokens, cost_estimate
        """
        model = self.models[task_type]
        config = MODEL_CONFIG[task_type]
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        # Add metadata for LangSmith
        run_metadata = {
            "task_type": task_type,
            "model_config": config,
            **(metadata or {})
        }
        
        # Execute with tracing
        response = await model.ainvoke(
            messages,
            config={"metadata": run_metadata}
        )
        
        # Extract usage stats
        input_tokens = response.usage_metadata.get("input_tokens", 0) if hasattr(response, 'usage_metadata') else 0
        output_tokens = response.usage_metadata.get("output_tokens", 0) if hasattr(response, 'usage_metadata') else 0
        
        # Calculate cost estimate
        if "sonnet" in config["model"]:
            cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000
        elif "haiku" in config["model"]:
            cost = (input_tokens * 0.0008 + output_tokens * 0.004) / 1000
        else:  # Gemini
            cost = (input_tokens * 0.00025 + output_tokens * 0.001) / 1000
        
        return {
            "response": response.content,
            "model_used": config["model"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_estimate": cost
        }


# ============================================================================
# LANGGRAPH NODES (with LangSmith tracing)
# ============================================================================

@traceable(name="parse_query", run_type="chain")
async def parse_query_node(state: AgentState) -> AgentState:
    """Parse and validate the research query"""
    state["current_step"] = "parse_query"
    
    query = state["query"]
    
    # Validate therapeutic area
    if query.therapeutic_area.lower() not in [ta.lower() for ta in THERAPEUTIC_AREAS]:
        state["errors"].append(f"Unknown therapeutic area: {query.therapeutic_area}")
    
    return state


@traceable(name="pubmed_search", run_type="retriever")
async def pubmed_search_node(state: AgentState) -> AgentState:
    """Search PubMed for peer-reviewed literature"""
    state["current_step"] = "pubmed_search"
    
    query = state["query"]
    client = PubMedClient()
    
    try:
        # Build optimized search query
        search_terms = f"{query.topic} AND {query.therapeutic_area}"
        
        # Add article type filters for better evidence
        article_types = ["Systematic Review", "Meta-Analysis", "Randomized Controlled Trial", 
                        "Clinical Trial", "Practice Guideline"]
        
        # Search
        pmids = await client.search(
            query=search_terms,
            max_results=query.max_results,
            date_range_years=query.date_range_years,
            article_types=article_types
        )
        
        # Fetch details
        articles = await client.fetch_details(pmids)
        
        # Filter by evidence level
        filtered = EvidenceGrader.filter_by_minimum_level(
            articles, 
            query.minimum_evidence_level
        )
        
        state["pubmed_results"] = filtered
        
    except Exception as e:
        state["errors"].append(f"PubMed search error: {str(e)}")
        state["pubmed_results"] = []
    
    finally:
        await client.close()
    
    return state


@traceable(name="perplexity_search", run_type="retriever")
async def perplexity_search_node(state: AgentState) -> AgentState:
    """Search Perplexity for additional academic sources"""
    state["current_step"] = "perplexity_search"
    
    query = state["query"]
    client = PerplexityClient()
    
    try:
        # Build academic-focused query
        search_query = (
            f"Find peer-reviewed clinical research on {query.topic} in {query.therapeutic_area}. "
            f"Focus on systematic reviews, meta-analyses, and randomized controlled trials "
            f"published in the last {query.date_range_years} years. "
            f"Include PMID or DOI for each source."
        )
        
        result = await client.search(search_query, focus="academic")
        
        # Validate citations
        validated_citations = []
        for citation in result.get("citations", []):
            is_valid, reason = SourceValidator.validate_citation(citation)
            if is_valid:
                validated_citations.append(citation)
        
        state["perplexity_results"] = [{
            "content": result["content"],
            "citations": validated_citations
        }]
        
    except Exception as e:
        state["errors"].append(f"Perplexity search error: {str(e)}")
        state["perplexity_results"] = []
    
    finally:
        await client.close()
    
    return state


@traceable(name="validate_sources", run_type="chain")
async def validate_sources_node(state: AgentState) -> AgentState:
    """Validate and deduplicate all sources"""
    state["current_step"] = "validate_sources"
    
    validated = []
    seen_pmids = set()
    seen_dois = set()
    
    # Process PubMed results
    for article in state.get("pubmed_results", []):
        pmid = article.get("pmid")
        doi = article.get("doi")
        
        # Skip duplicates
        if pmid and pmid in seen_pmids:
            continue
        if doi and doi in seen_dois:
            continue
        
        # Validate
        is_valid, reason = SourceValidator.validate_citation(article)
        if is_valid:
            citation = Citation(
                pmid=pmid,
                doi=doi,
                title=article.get("title", ""),
                authors=article.get("authors", []),
                journal=article.get("journal", ""),
                year=article.get("year", 0),
                abstract=article.get("abstract", ""),
                evidence_level=article.get("evidence_level", EvidenceLevel.LEVEL_5),
                source_type=SourceType.PUBMED,
                url=article.get("url", "")
            )
            validated.append(citation)
            
            if pmid:
                seen_pmids.add(pmid)
            if doi:
                seen_dois.add(doi)
    
    state["validated_citations"] = validated
    
    return state


@traceable(name="synthesize_findings", run_type="chain")
async def synthesize_findings_node(state: AgentState) -> AgentState:
    """Synthesize findings using appropriate LLM"""
    state["current_step"] = "synthesize_findings"
    
    query = state["query"]
    citations = state.get("validated_citations", [])
    
    if not citations:
        state["synthesis"] = "No peer-reviewed evidence found matching criteria."
        return state
    
    router = LLMRouter()
    
    # Build synthesis prompt
    citation_summaries = "\n".join([
        f"- {c.title} ({c.journal}, {c.year}) [Evidence: {c.evidence_level.value}]\n  Abstract: {c.abstract[:500]}..."
        for c in citations[:20]  # Limit to top 20 for context
    ])
    
    system_prompt = """You are a medical education specialist creating content for CME programs.
Your task is to synthesize peer-reviewed evidence into actionable clinical insights.

REQUIREMENTS:
1. Only reference the provided peer-reviewed sources
2. Identify clinical practice gaps
3. Highlight key findings with evidence levels
4. Provide recommendations based on evidence strength
5. Use language appropriate for healthcare professionals
6. Include specific data points (percentages, NNT, odds ratios, etc.)
"""
    
    synthesis_prompt = f"""
Research Query: {query.topic}
Therapeutic Area: {query.therapeutic_area}
Query Type: {query.query_type}
Target Audience: {query.target_audience}

Peer-Reviewed Evidence:
{citation_summaries}

Please synthesize these findings into a comprehensive evidence summary that:
1. Identifies 3-5 key clinical practice gaps
2. Summarizes the strongest evidence (Level 1-2)
3. Provides evidence-based recommendations
4. Notes any conflicting findings or limitations
5. Suggests areas needing further research

Format your response with clear sections and cite sources by title/year.
"""
    
    result = await router.route_and_execute(
        task_type="complex_synthesis",
        prompt=synthesis_prompt,
        system_prompt=system_prompt
    )
    
    state["synthesis"] = result["response"]
    state["model_used"] = result["model_used"]
    state["tokens_used"] = result["input_tokens"] + result["output_tokens"]
    state["cost_estimate"] = result["cost_estimate"]
    
    return state


@traceable(name="extract_gaps", run_type="chain")
async def extract_gaps_node(state: AgentState) -> AgentState:
    """Extract clinical gaps from synthesis"""
    state["current_step"] = "extract_gaps"
    
    router = LLMRouter()
    
    extraction_prompt = f"""
From this evidence synthesis, extract:
1. Clinical practice gaps (list format)
2. Key findings (list format)
3. Evidence-based recommendations (list format)

Synthesis:
{state.get('synthesis', '')}

Format as JSON:
{{
    "clinical_gaps": ["gap1", "gap2", ...],
    "key_findings": ["finding1", "finding2", ...],
    "recommendations": ["rec1", "rec2", ...]
}}
"""
    
    result = await router.route_and_execute(
        task_type="citation_extraction",  # Use cheaper model for extraction
        prompt=extraction_prompt
    )
    
    try:
        # Parse JSON response
        import re
        json_match = re.search(r'\{[\s\S]*\}', result["response"])
        if json_match:
            extracted = json.loads(json_match.group())
            state["clinical_gaps"] = extracted.get("clinical_gaps", [])
            state["key_findings"] = extracted.get("key_findings", [])
    except json.JSONDecodeError:
        state["errors"].append("Failed to parse extraction response")
    
    return state


@traceable(name="compile_result", run_type="chain")
async def compile_result_node(state: AgentState) -> AgentState:
    """Compile final research result"""
    state["current_step"] = "compile_result"
    
    # Build evidence summary
    evidence_summary = {}
    for citation in state.get("validated_citations", []):
        level = citation.evidence_level.value
        evidence_summary[level] = evidence_summary.get(level, 0) + 1
    
    result = ResearchResult(
        query=state["query"],
        citations=state.get("validated_citations", []),
        synthesis=state.get("synthesis", ""),
        clinical_gaps=state.get("clinical_gaps", []),
        key_findings=state.get("key_findings", []),
        recommendations=[],  # Populated from synthesis
        evidence_summary=evidence_summary,
        metadata={
            "model_used": state.get("model_used", ""),
            "tokens_used": state.get("tokens_used", 0),
            "cost_estimate": state.get("cost_estimate", 0),
            "errors": state.get("errors", []),
            "timestamp": datetime.now().isoformat()
        }
    )
    
    state["final_result"] = result
    
    return state


# ============================================================================
# BUILD LANGGRAPH
# ============================================================================

def build_research_graph() -> StateGraph:
    """Build the research agent graph"""
    
    # Create graph
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("parse_query", parse_query_node)
    graph.add_node("pubmed_search", pubmed_search_node)
    graph.add_node("perplexity_search", perplexity_search_node)
    graph.add_node("validate_sources", validate_sources_node)
    graph.add_node("synthesize_findings", synthesize_findings_node)
    graph.add_node("extract_gaps", extract_gaps_node)
    graph.add_node("compile_result", compile_result_node)
    
    # Define edges
    graph.set_entry_point("parse_query")
    
    # Parallel search
    graph.add_edge("parse_query", "pubmed_search")
    graph.add_edge("parse_query", "perplexity_search")
    
    # Merge and validate
    graph.add_edge("pubmed_search", "validate_sources")
    graph.add_edge("perplexity_search", "validate_sources")
    
    # Sequential processing
    graph.add_edge("validate_sources", "synthesize_findings")
    graph.add_edge("synthesize_findings", "extract_gaps")
    graph.add_edge("extract_gaps", "compile_result")
    graph.add_edge("compile_result", END)
    
    return graph.compile()


# ============================================================================
# MAIN AGENT CLASS (with LangSmith Cloud)
# ============================================================================

class CMEResearchAgent:
    """
    Main research agent for DHG CME division.
    
    LangSmith Cloud integration for full observability.
    
    Usage:
        agent = CMEResearchAgent()
        result = await agent.research(
            topic="chronic cough management",
            therapeutic_area="pulmonology",
            query_type="gap_analysis"
        )
    """
    
    def __init__(self, project_name: str = "dhg-cme-research-agent"):
        self.graph = build_research_graph()
        self.project_name = project_name
        self.langsmith_client = langsmith_client
        
        # Set project for this session
        os.environ["LANGCHAIN_PROJECT"] = project_name
    
    @traceable(name="cme_research_workflow", run_type="chain")
    async def research(
        self,
        topic: str,
        therapeutic_area: str,
        query_type: Literal["gap_analysis", "needs_assessment", "literature_review", "podcast_content", "cme_content"] = "gap_analysis",
        target_audience: str = "primary_care",
        date_range_years: int = 5,
        minimum_evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_2B,
        max_results: int = 50,
        specific_questions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> ResearchResult:
        """
        Execute research workflow with full LangSmith tracing.
        
        Args:
            topic: Research topic (e.g., "chronic cough management")
            therapeutic_area: Medical specialty
            query_type: Type of research output needed
            target_audience: Who will consume the content
            date_range_years: Limit to publications within N years
            minimum_evidence_level: Minimum acceptable evidence level
            max_results: Maximum number of citations
            specific_questions: Additional research questions
            tags: LangSmith tags for filtering runs
        
        Returns:
            ResearchResult with citations, synthesis, and gaps
        """
        query = ResearchQuery(
            topic=topic,
            therapeutic_area=therapeutic_area,
            query_type=query_type,
            target_audience=target_audience,
            date_range_years=date_range_years,
            minimum_evidence_level=minimum_evidence_level,
            max_results=max_results,
            specific_questions=specific_questions or []
        )
        
        initial_state: AgentState = {
            "query": query,
            "messages": [],
            "pubmed_results": [],
            "perplexity_results": [],
            "validated_citations": [],
            "synthesis": "",
            "clinical_gaps": [],
            "key_findings": [],
            "final_result": None,
            "current_step": "",
            "errors": [],
            "model_used": "",
            "tokens_used": 0,
            "cost_estimate": 0.0
        }
        
        # LangSmith run config
        run_config = {
            "metadata": {
                "topic": topic,
                "therapeutic_area": therapeutic_area,
                "query_type": query_type,
                "target_audience": target_audience,
                "agent_version": "1.1.0"
            },
            "tags": tags or [therapeutic_area, query_type]
        }
        
        # Execute graph with tracing
        final_state = await self.graph.ainvoke(
            initial_state,
            config=run_config
        )
        
        return final_state["final_result"]
    
    def submit_feedback(
        self,
        run_id: str,
        score: float,
        comment: Optional[str] = None,
        key: str = "quality"
    ):
        """
        Submit feedback to LangSmith for a specific run.
        
        Args:
            run_id: The LangSmith run ID
            score: Score between 0 and 1
            comment: Optional feedback comment
            key: Feedback key (e.g., "quality", "accuracy", "relevance")
        """
        self.langsmith_client.create_feedback(
            run_id=run_id,
            key=key,
            score=score,
            comment=comment
        )
    
    def create_dataset(
        self,
        name: str,
        description: str,
        examples: List[dict]
    ) -> str:
        """
        Create a LangSmith dataset for evaluation.
        
        Args:
            name: Dataset name
            description: Dataset description
            examples: List of {"input": {...}, "output": {...}} dicts
        
        Returns:
            Dataset ID
        """
        dataset = self.langsmith_client.create_dataset(
            name,
            description=description
        )
        
        for example in examples:
            self.langsmith_client.create_example(
                inputs=example["input"],
                outputs=example.get("output"),
                dataset_id=dataset.id
            )
        
        return dataset.id
    
    def export_to_json(self, result: ResearchResult, filepath: str):
        """Export result to JSON file"""
        output = {
            "query": {
                "topic": result.query.topic,
                "therapeutic_area": result.query.therapeutic_area,
                "query_type": result.query.query_type,
                "target_audience": result.query.target_audience
            },
            "citations": [c.to_dict() for c in result.citations],
            "synthesis": result.synthesis,
            "clinical_gaps": result.clinical_gaps,
            "key_findings": result.key_findings,
            "evidence_summary": result.evidence_summary,
            "metadata": result.metadata
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
    
    def export_citations_ama(self, result: ResearchResult) -> str:
        """Export citations in AMA format for CME materials"""
        citations = []
        for i, c in enumerate(result.citations, 1):
            citations.append(f"{i}. {c.to_ama_format()}")
        return "\n".join(citations)


# ============================================================================
# CLI INTERFACE
# ============================================================================

async def main():
    """Example usage"""
    agent = CMEResearchAgent()
    
    # Example: Chronic cough gap analysis (relevant to GSK grant)
    result = await agent.research(
        topic="chronic cough refractory treatment guidelines",
        therapeutic_area="pulmonology",
        query_type="gap_analysis",
        target_audience="primary_care",
        date_range_years=5,
        minimum_evidence_level=EvidenceLevel.LEVEL_2B,
        specific_questions=[
            "What are current guideline recommendations for chronic cough?",
            "What gaps exist in primary care management of chronic cough?",
            "What new therapeutic options are emerging?"
        ]
    )
    
    print("=" * 80)
    print("CME RESEARCH AGENT RESULTS")
    print("=" * 80)
    print(f"\nTopic: {result.query.topic}")
    print(f"Citations Found: {len(result.citations)}")
    print(f"\nEvidence Distribution:")
    for level, count in result.evidence_summary.items():
        print(f"  {level}: {count}")
    
    print(f"\n{'='*80}")
    print("CLINICAL GAPS IDENTIFIED:")
    print("=" * 80)
    for i, gap in enumerate(result.clinical_gaps, 1):
        print(f"{i}. {gap}")
    
    print(f"\n{'='*80}")
    print("SYNTHESIS:")
    print("=" * 80)
    print(result.synthesis)
    
    # Export
    agent.export_to_json(result, "research_output.json")
    print(f"\nResults exported to research_output.json")


if __name__ == "__main__":
    asyncio.run(main())
