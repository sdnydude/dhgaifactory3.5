"""
DHG CME Research Agent - LangGraph Cloud Ready
===============================================
Evidence-based research agent for clinical gap analysis, needs assessments,
and CME content development.

LANGGRAPH CLOUD READY:
- No Docker
- No FastAPI  
- No PostgreSQL
- No Redis
- Pure LangGraph + LangSmith

LLM PROVIDERS:
- Claude Sonnet 4 (Anthropic) - Complex synthesis, CME content
- Claude Haiku (Anthropic) - Extraction, structured output
- Gemini 2.5 Flash (Google) - Bulk screening, fast tasks
- Qwen 3 14B (Ollama) - Local processing, cost-free

AI FACTORY INTEGRATION:
- Central registry for service discovery
- Standardized agent manifest
- Model availability reporting

Author: Digital Harmony Group
Version: 2.1.0 (Cloud + Ollama + Registry)
"""

import os

# Load secrets from Infisical at startup
import json
from datetime import datetime
import operator
from typing import Annotated, Literal, Optional, List, Dict, Any
from typing_extensions import TypedDict
from dataclasses import dataclass, field
from enum import Enum

# LangGraph Cloud compatible imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable

# LangChain for LLM calls (LangSmith native tracing)
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

# HTTP for external APIs
import httpx


# =============================================================================
# CONFIGURATION
# =============================================================================

THERAPEUTIC_AREAS = [
    "cardiology", "oncology", "neurology", "pulmonology", "gastroenterology",
    "endocrinology", "rheumatology", "infectious_disease", "dermatology",
    "psychiatry", "nephrology", "hematology", "immunology", "primary_care",
    "pediatrics", "geriatrics", "emergency_medicine", "critical_care"
]


class EvidenceLevel(Enum):
    """Oxford Centre for Evidence-Based Medicine Levels"""
    LEVEL_1A = "systematic_review_meta_analysis"
    LEVEL_1B = "high_quality_rct"
    LEVEL_2A = "lower_quality_rct"
    LEVEL_2B = "cohort_case_control"
    LEVEL_3 = "case_series"
    LEVEL_4 = "expert_opinion"
    LEVEL_5 = "narrative_review"


class SourceType(Enum):
    """Allowed source types for CME content"""
    PUBMED = "pubmed"
    COCHRANE = "cochrane"
    CLINICAL_TRIALS = "clinicaltrials_gov"
    FDA = "fda_labels"
    PRACTICE_GUIDELINE = "practice_guideline"
    PERPLEXITY_ACADEMIC = "perplexity_academic"


# =============================================================================
# AI FACTORY CENTRAL REGISTRY SCHEMA & CLIENT
# =============================================================================

class AIFactoryRegistry:
    """
    Central registry client for DHG AI Factory v3.5.
    
    Schema:
    - Services register with standardized manifest
    - Models report availability and capabilities
    - Enables service discovery and load balancing
    """
    
    def __init__(self, registry_url: Optional[str] = None):
        self.registry_url = registry_url or os.getenv(
            "AI_FACTORY_REGISTRY_URL",
            "http://10.0.0.251:8500"
        )
        self.service_id = "cme-research-agent"
        self.version = "2.1.0"
    
    def get_agent_manifest(self) -> dict:
        """
        Standardized agent manifest for AI Factory registry.
        
        This schema is used across all DHG AI Factory agents.
        """
        return {
            # === SERVICE IDENTITY ===
            "service": {
                "id": self.service_id,
                "name": "CME Research Agent",
                "version": self.version,
                "division": "DHG CME",
                "type": "research_agent",
                "description": "Evidence-based research for clinical gap analysis and CME content"
            },
            
            # === CAPABILITIES ===
            "capabilities": {
                "primary": [
                    "clinical_gap_analysis",
                    "needs_assessment",
                    "literature_review",
                    "evidence_synthesis"
                ],
                "secondary": [
                    "podcast_content",
                    "cme_content",
                    "citation_management"
                ]
            },
            
            # === INPUT/OUTPUT SCHEMA ===
            "io_schema": {
                "inputs": {
                    "topic": {"type": "string", "required": True},
                    "therapeutic_area": {"type": "string", "required": True},
                    "query_type": {
                        "type": "string",
                        "default": "gap_analysis",
                        "enum": ["gap_analysis", "needs_assessment", "literature_review", "podcast_content", "cme_content"]
                    },
                    "target_audience": {
                        "type": "string",
                        "default": "primary_care",
                        "enum": ["primary_care", "specialist", "np_pa", "pharmacist", "nurse", "mixed"]
                    },
                    "date_range_years": {"type": "integer", "default": 5},
                    "max_results": {"type": "integer", "default": 50},
                    "use_local_llm": {"type": "boolean", "default": False}
                },
                "outputs": {
                    "synthesis": {"type": "string"},
                    "clinical_gaps": {"type": "array"},
                    "key_findings": {"type": "array"},
                    "validated_citations": {"type": "array"},
                    "model_used": {"type": "string"},
                    "total_tokens": {"type": "integer"},
                    "total_cost": {"type": "number"}
                }
            },
            
            # === AVAILABLE MODELS ===
            "models": self._get_model_registry(),
            
            # === EXTERNAL DEPENDENCIES ===
            "external_apis": [
                {
                    "name": "PubMed",
                    "type": "retriever",
                    "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
                    "auth_required": False,
                    "rate_limit": "10/sec with key"
                },
                {
                    "name": "Perplexity",
                    "type": "retriever",
                    "endpoint": "https://api.perplexity.ai",
                    "auth_required": True
                }
            ],
            
            # === OBSERVABILITY ===
            "observability": {
                "langsmith_project": "dhg-cme-research-agent",
                "tracing": True
            }
        }
    
    def _get_model_registry(self) -> dict:
        """Get available models with current status"""
        return {
            "claude_sonnet": {
                "provider": "anthropic",
                "model_id": "claude-3-5-sonnet-20241022",
                "status": "available" if os.getenv("ANTHROPIC_API_KEY") else "no_api_key",
                "use_cases": ["complex_synthesis", "cme_content"],
                "cost": {"input": 0.003, "output": 0.015},
                "context_window": 200000,
                "max_output": 8192
            },
            "gemini_flash": {
                "provider": "google",
                "model_id": "gemini-1.5-flash",
                "status": "available" if os.getenv("GOOGLE_API_KEY") else "no_api_key",
                "use_cases": ["bulk_screening", "fast_tasks"],
                "cost": {"input": 0.00025, "output": 0.001},
                "context_window": 1000000,
                "max_output": 4096
            }
        }
    
    async def register(self) -> dict:
        """Register with AI Factory central registry"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.registry_url}/api/v1/agents/register",
                    json=self.get_agent_manifest()
                )
                if response.status_code == 200:
                    return {"status": "registered", "data": response.json()}
                return {"status": "failed", "code": response.status_code}
        except Exception as e:
            return {"status": "registry_unavailable", "error": str(e)}
    
    async def heartbeat(self, metrics: Optional[dict] = None) -> bool:
        """Send heartbeat with metrics"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(
                    f"{self.registry_url}/api/v1/agents/{self.service_id}/heartbeat",
                    json={"status": "healthy", "models": self._get_model_registry(), "metrics": metrics or {}}
                )
                return response.status_code == 200
        except Exception:
            return False

    async def log_research_request(self, topic: str, user_id: str, input_params: dict) -> Optional[str]:
        """Log a new research request to the registry"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.registry_url}/api/v1/research/requests",
                    json={
                        "user_id": user_id,
                        "agent_type": "cme_research",
                        "input_params": input_params
                    }
                )
                if response.status_code == 201:
                    return response.json().get("request_id")
                return None
        except Exception:
            return None

    async def update_research_request(self, request_id: str, status: str, output_summary: dict = None, metadata: dict = None, error: str = None) -> bool:
        """Update research request status and results in the registry"""
        try:
            payload = {"status": status}
            if output_summary:
                payload["output_summary"] = output_summary
            if metadata:
                payload["processing_metadata"] = metadata
            if error:
                payload["error_message"] = error
            if status == "completed":
                payload["completed_at"] = datetime.utcnow().isoformat()

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.patch(
                    f"{self.registry_url}/api/v1/research/requests/{request_id}",
                    json=payload
                )
                return response.status_code == 200
        except Exception:
            return False
registry = AIFactoryRegistry()


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Citation:
    """Structured citation for CME compliance"""
    pmid: Optional[str] = None
    doi: Optional[str] = None
    title: str = ""
    authors: List[str] = field(default_factory=list)
    journal: str = ""
    year: int = 0
    abstract: str = ""
    evidence_level: EvidenceLevel = EvidenceLevel.LEVEL_5
    url: str = ""
    
    def to_ama_format(self) -> str:
        author_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            author_str += ", et al"
        return f"{author_str}. {self.title}. {self.journal}. {self.year}."


# =============================================================================
# STATE DEFINITION
# =============================================================================

class AgentState(TypedDict):
    """State passed between nodes"""
    # Tracking
    request_id: Optional[str]
    user_id: str

    """State passed between nodes"""
    # Input
    topic: str
    therapeutic_area: str
    query_type: str
    target_audience: str
    date_range_years: int
    minimum_evidence_level: str
    max_results: int
    output_format: str  # json, cme_proposal, podcast_script, gap_report, powerpoint_outline
    specific_questions: List[str]
    use_local_llm: bool
    
    # Processing
    messages: Annotated[list, add_messages]
    pubmed_results: Annotated[List[dict], operator.add]
    perplexity_results: Annotated[List[dict], operator.add]
    validated_citations: List[dict]
    
    # Output
    synthesis: str
    clinical_gaps: List[str]
    key_findings: List[str]
    
    # Metadata
    errors: Annotated[List[str], operator.add]
    model_used: str
    total_tokens: int
    total_cost: float


# =============================================================================
# LLM ROUTER (Claude + Gemini + Qwen3 Ollama)
# =============================================================================

class LLMRouter:
    """
    Multi-provider LLM router.
    
    Models:
    - Claude Sonnet 4: Best quality
    - Claude Haiku: Fast extraction
    - Gemini Flash: Bulk processing
    - Qwen3 14B (Ollama): Local, free
    """
    
    def __init__(self, prefer_local: bool = False):
        self.prefer_local = prefer_local
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._cache = {}
    
    def _get_claude_sonnet(self):
        if "claude_sonnet" not in self._cache:
            self._cache["claude_sonnet"] = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192
            )
        return self._cache["claude_sonnet"]
    
    def _get_claude_haiku(self):
        if "claude_haiku" not in self._cache:
            self._cache["claude_haiku"] = ChatAnthropic(
                model="claude-3-5-haiku-20241022",
                max_tokens=2048
            )
        return self._cache["claude_haiku"]
    
    def _get_gemini_flash(self):
        if "gemini_flash" not in self._cache:
            self._cache["gemini_flash"] = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                max_output_tokens=4096
            )
        return self._cache["gemini_flash"]
    
    def _get_qwen_local(self):
        if "qwen_local" not in self._cache:
            self._cache["qwen_local"] = ChatOllama(
                model="qwen3:14b",
                base_url=self.ollama_url,
                num_ctx=32000
            )
        return self._cache["qwen_local"]
    
    def get_model(self, task: str, force_local: bool = False) -> tuple:
        """Get model for task. Returns (model, name, cost_per_1k_output)"""
        if force_local or self.prefer_local:
            return (self._get_qwen_local(), "qwen3:14b", 0.0)
        
        if task == "complex_synthesis":
            return (self._get_claude_sonnet(), "claude-sonnet-3.5", 0.015)
        elif task == "cme_content":
            return (self._get_claude_sonnet(), "claude-sonnet-3.5", 0.015)
        else:
            return (self._get_claude_haiku(), "claude-haiku-3.5", 0.00025)
            return (self._get_qwen_local(), "qwen3:14b", 0.0)
        
        if task == "complex_synthesis":
             return (self._get_gemini_pro(), "gemini-1.5-pro", 0.0105)
        elif task == "cme_content":
             return (self._get_gemini_pro(), "gemini-1.5-pro", 0.0105)
        else:
             return (self._get_gemini_flash(), "gemini-1.5-flash", 0.0003)
        if task == "complex_synthesis":
            return (self._get_claude_sonnet(), "claude-sonnet-4-20250514", 0.015)
        elif task == "extraction":
            return (self._get_claude_haiku(), "claude-3-5-haiku-20241022", 0.004)
        elif task == "bulk_screening":
            return (self._get_gemini_flash(), "gemini-2.5-flash-preview-05-20", 0.001)
        else:
            return (self._get_claude_sonnet(), "claude-sonnet-4-20250514", 0.015)
    
    @traceable(name="llm_invoke", run_type="llm")
    async def invoke(self, task: str, messages: List, force_local: bool = False, metadata: Optional[dict] = None) -> dict:
        """Invoke LLM with routing"""
        model, model_name, cost_rate = self.get_model(task, force_local)
        
        config = {"metadata": {"task": task, "model": model_name, "local": "qwen" in model_name.lower(), **(metadata or {})}}
        response = await model.ainvoke(messages, config=config)
        
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = response.usage_metadata.get("input_tokens", 0)
            output_tokens = response.usage_metadata.get("output_tokens", 0)
        
        # Estimate for Ollama
        if "qwen" in model_name.lower() and not input_tokens:
            input_tokens = sum(len(str(m.content)) // 4 for m in messages)
            output_tokens = len(response.content) // 4
        
        return {
            "response": response.content,
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": (output_tokens * cost_rate) / 1000,
            "local": "qwen" in model_name.lower()
        }


# =============================================================================
# PUBMED CLIENT
# =============================================================================

class PubMedClient:
    """PubMed E-Utilities API client"""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self):
        self.api_key = os.getenv("NCBI_API_KEY")
        self.email = os.getenv("NCBI_EMAIL", "research@digitalharmonygroup.com")
    
    @traceable(name="pubmed_search", run_type="retriever")
    async def search(self, query: str, max_results: int = 50, date_range_years: int = 5) -> List[str]:
        search_query = f"{query} AND ({date_range_years}y[dp])"
        type_filter = '"Systematic Review"[pt] OR "Meta-Analysis"[pt] OR "Randomized Controlled Trial"[pt] OR "Clinical Trial"[pt] OR "Practice Guideline"[pt]'
        search_query += f" AND ({type_filter})"
        
        params = {"db": "pubmed", "term": search_query, "retmax": max_results, "retmode": "json", "sort": "relevance", "email": self.email}
        if self.api_key:
            params["api_key"] = self.api_key
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
            response.raise_for_status()
            return response.json().get("esearchresult", {}).get("idlist", [])
    
    @traceable(name="pubmed_fetch", run_type="retriever")
    async def fetch_details(self, pmids: List[str]) -> List[dict]:
        if not pmids:
            return []
        
        params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", "email": self.email}
        if self.api_key:
            params["api_key"] = self.api_key
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
            response.raise_for_status()
            return self._parse_xml(response.text)
    
    def _parse_xml(self, xml_text: str) -> List[dict]:
        import xml.etree.ElementTree as ET
        articles = []
        try:
            root = ET.fromstring(xml_text)
            for article in root.findall(".//PubmedArticle"):
                try:
                    medline = article.find(".//MedlineCitation")
                    article_data = medline.find(".//Article")
                    pmid = medline.find(".//PMID").text
                    title_elem = article_data.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None and title_elem.text else ""
                    
                    authors = []
                    for author in article_data.findall(".//Author"):
                        lastname = author.find("LastName")
                        if lastname is not None and lastname.text:
                            authors.append(lastname.text)
                    
                    journal = article_data.find(".//Journal")
                    journal_title = ""
                    year = ""
                    if journal is not None:
                        jt = journal.find(".//Title")
                        journal_title = jt.text if jt is not None else ""
                        pub_date = journal.find(".//PubDate")
                        if pub_date is not None:
                            year_elem = pub_date.find("Year")
                            year = year_elem.text if year_elem is not None else ""
                    
                    abstract_elem = article_data.find(".//Abstract/AbstractText")
                    abstract = abstract_elem.text if abstract_elem is not None and abstract_elem.text else ""
                    pub_types = [pt.text for pt in medline.findall(".//PublicationType") if pt.text]
                    
                    doi = ""
                    for id_elem in article.findall(".//ArticleId"):
                        if id_elem.get("IdType") == "doi":
                            doi = id_elem.text or ""
                            break
                    
                    articles.append({
                        "pmid": pmid, "doi": doi, "title": title, "authors": authors,
                        "journal": journal_title, "year": int(year) if year.isdigit() else 0,
                        "abstract": abstract, "publication_types": pub_types,
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
    """Perplexity API with academic focus"""
    
    ACADEMIC_DOMAINS = [
        "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "cochranelibrary.com",
        "jamanetwork.com", "nejm.org", "thelancet.com", "bmj.com",
        "nature.com", "sciencedirect.com", "nih.gov", "cdc.gov", "fda.gov"
    ]
    
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
    
    @traceable(name="perplexity_search", run_type="retriever")
    async def search(self, query: str) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": "You are a medical research assistant. ONLY cite peer-reviewed publications. Include PMID or DOI."},
                {"role": "user", "content": query}
            ],
            "return_citations": True,
            "search_domain_filter": self.ACADEMIC_DOMAINS
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return {"content": data["choices"][0]["message"]["content"], "citations": data.get("citations", [])}


# =============================================================================
# EVIDENCE GRADER & VALIDATOR
# =============================================================================

class EvidenceGrader:
    PUBTYPE_MAPPING = {
        "Systematic Review": EvidenceLevel.LEVEL_1A,
        "Meta-Analysis": EvidenceLevel.LEVEL_1A,
        "Randomized Controlled Trial": EvidenceLevel.LEVEL_1B,
        "Clinical Trial": EvidenceLevel.LEVEL_2A,
        "Cohort Study": EvidenceLevel.LEVEL_2B,
        "Practice Guideline": EvidenceLevel.LEVEL_4,
        "Review": EvidenceLevel.LEVEL_5,
    }
    
    @classmethod
    def grade(cls, pub_types: List[str]) -> EvidenceLevel:
        best = EvidenceLevel.LEVEL_5
        for pt in pub_types:
            if pt in cls.PUBTYPE_MAPPING:
                level = cls.PUBTYPE_MAPPING[pt]
                if list(EvidenceLevel).index(level) < list(EvidenceLevel).index(best):
                    best = level
        return best
    
    @classmethod
    def filter_by_level(cls, articles: List[dict], min_level: EvidenceLevel) -> List[dict]:
        min_idx = list(EvidenceLevel).index(min_level)
        result = []
        for a in articles:
            level = cls.grade(a.get("publication_types", []))
            if list(EvidenceLevel).index(level) <= min_idx:
                a["evidence_level"] = level.value
                result.append(a)
        return result


class SourceValidator:
    BLOCKED = {"wikipedia.org", "webmd.com", "healthline.com", "medscape.com", "reddit.com"}
    
    @classmethod
    def validate(cls, c: dict) -> bool:
        if not c.get("pmid") and not c.get("doi"):
            return False
        if not c.get("year") or c.get("year", 0) < 1900:
            return False
        if not c.get("title"):
            return False
        url = c.get("url", "").lower()
        return not any(b in url for b in cls.BLOCKED)


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="pubmed_search_node", run_type="chain")
async def pubmed_search_node(state: AgentState) -> dict:
    client = PubMedClient()
    try:
        pmids = await client.search(
            f"{state['topic']} AND {state['therapeutic_area']}",
            state.get("max_results", 50),
            state.get("date_range_years", 5)
        )
        articles = await client.fetch_details(pmids)
        min_level = EvidenceLevel(state.get("minimum_evidence_level", "cohort_case_control"))
        filtered = EvidenceGrader.filter_by_level(articles, min_level)
        return {"pubmed_results": filtered, "errors": state.get("errors", [])}
    except Exception as e:
        errors = state.get("errors", [])
        errors.append(f"PubMed: {e}")
        return {"pubmed_results": [], "errors": errors}


@traceable(name="perplexity_search_node", run_type="chain")
async def perplexity_search_node(state: AgentState) -> dict:
    client = PerplexityClient()
    try:
        query = f"Find peer-reviewed research on {state['topic']} in {state['therapeutic_area']}. Focus on systematic reviews and RCTs from last {state.get('date_range_years', 5)} years. Include PMID/DOI."
        result = await client.search(query)
        return {"perplexity_results": [result], "errors": state.get("errors", [])}
    except Exception as e:
        errors = state.get("errors", [])
        errors.append(f"Perplexity: {e}")
        return {"perplexity_results": [], "errors": errors}


@traceable(name="validate_sources_node", run_type="chain")
async def validate_sources_node(state: AgentState) -> dict:
    validated = []
    seen = set()
    for a in state.get("pubmed_results", []):
        key = a.get("pmid") or a.get("doi")
        if key and key not in seen and SourceValidator.validate(a):
            validated.append(a)
            seen.add(key)
    return {"validated_citations": validated}


@traceable(name="synthesize_node", run_type="chain")
async def synthesize_node(state: AgentState) -> dict:
    citations = state.get("validated_citations", [])
    use_local = state.get("use_local_llm", False)
    
    if not citations:
        return {"synthesis": "No peer-reviewed evidence found.", "model_used": "none", "total_tokens": 0, "total_cost": 0.0}
    
    router = LLMRouter(prefer_local=use_local)
    
    citation_text = "\n".join([
        f"- {c['title']} ({c['journal']}, {c['year']}) [Evidence: {c.get('evidence_level', '?')}]\n  {c.get('abstract', '')[:400]}..."
        for c in citations[:20]
    ])
    
    system = "You are a medical education specialist. Synthesize evidence into clinical insights. Identify practice gaps."
    prompt = f"""Topic: {state['topic']}
Area: {state['therapeutic_area']}
Audience: {state['target_audience']}

Evidence:
{citation_text}

Synthesize:
1. 3-5 clinical practice gaps
2. Key evidence summary
3. Recommendations
4. Conflicting findings
5. Research needs"""
    
    result = await router.invoke("complex_synthesis", [SystemMessage(content=system), HumanMessage(content=prompt)], force_local=use_local)
    return {"synthesis": result["response"], "model_used": result["model"], "total_tokens": result["total_tokens"], "total_cost": result["cost"]}


@traceable(name="extract_gaps_node", run_type="chain")
async def extract_gaps_node(state: AgentState) -> dict:
    router = LLMRouter(prefer_local=state.get("use_local_llm", False))
    prompt = f'Extract from synthesis:\n{state.get("synthesis", "")}\n\nRespond with JSON only:\n{{"clinical_gaps": ["..."], "key_findings": ["..."]}}'
    
    result = await router.invoke("extraction", [HumanMessage(content=prompt)], force_local=state.get("use_local_llm", False))
    
    try:
        import re
        match = re.search(r'\{[\s\S]*\}', result["response"])
        if match:
            data = json.loads(match.group())
            return {"clinical_gaps": data.get("clinical_gaps", []), "key_findings": data.get("key_findings", [])}
    except Exception:
        pass
    return {"clinical_gaps": [], "key_findings": []}


# =============================================================================

@traceable(name="log_request_node", run_type="chain")
async def log_request_node(state: AgentState, config: RunnableConfig) -> dict:
    """Log the start of the research request to the registry and apply config overrides"""
    # Get values from config (enables LangGraph Cloud Assistants)
    conf = config.get("configurable", {})
    
    # Merge config overrides into state values
    # Priorities: 1. Value in state (explicit prompt) 2. Value in config (Assistant default) 3. Hardcoded default
    output_format = state.get("output_format") or conf.get("output_format", "json")
    max_results = state.get("max_results") or conf.get("max_results", 50)
    date_range_years = state.get("date_range_years") or conf.get("date_range_years", 5)
    min_evidence = state.get("minimum_evidence_level") or conf.get("minimum_evidence_level", "LEVEL_3")
    use_local = state.get("use_local_llm") or conf.get("use_local_llm", False)
    
    update_payload = {
        "output_format": output_format,
        "max_results": max_results,
        "date_range_years": date_range_years,
        "minimum_evidence_level": min_evidence,
        "use_local_llm": use_local
    }
    
    if not state.get("request_id"):
        input_params = {
            "topic": state.get("topic"),
            "therapeutic_area": state.get("therapeutic_area"),
            "query_type": state.get("query_type"),
            "target_audience": state.get("target_audience"),
            "date_range_from": datetime.utcnow().isoformat(),
            "date_range_to": datetime.utcnow().isoformat(),
            "max_results": max_results,
            "output_format": output_format,
            "use_local_llm": use_local
        }
        req_id = await registry.log_research_request(
            state.get("topic"),
            state.get("user_id", "anonymous"),
            input_params
        )
        if req_id:
            await registry.update_research_request(req_id, "running")
            update_payload["request_id"] = req_id
            
    return update_payload
@traceable(name="finalize_node", run_type="chain")
async def finalize_node(state: AgentState, config: RunnableConfig) -> dict:
    """Final log update to the registry"""
    if state.get("request_id"):
        output_summary = {
            "gaps_identified": len(state.get("clinical_gaps", [])),
            "key_findings_count": len(state.get("key_findings", [])),
            "citations_count": len(state.get("validated_citations", [])),
            "output_format_used": state.get("output_format")
        }
        metadata = {
            "model_used": state.get("model_used"),
            "total_tokens": state.get("total_tokens"),
            "total_cost": state.get("total_cost"),
            "pubmed_results_count": len(state.get("pubmed_results", [])),
            "perplexity_results_count": len(state.get("perplexity_results", []))
        }
        await registry.update_research_request(
            state.get("request_id"),
            "completed",
            output_summary=output_summary,
            metadata=metadata
        )
    return {}
# BUILD GRAPH
# =============================================================================


# =============================================================================
# FILE SAVING UTILITIES
# =============================================================================

def save_research_output(
    content: str,
    topic: str,
    output_format: str,
    file_format: str = "md",
    base_dir: str = "./outputs",
    evaluation: dict = None
) -> str:
    """
    Save research output to file with optional evaluation metadata.
    
    Args:
        content: Rendered content to save
        topic: Research topic (used in filename)
        output_format: Format type (cme_proposal, podcast_script, etc.)
        file_format: File extension (md or txt)
        base_dir: Directory to save files
        evaluation: Optional evaluation results to prepend
    
    Returns:
        Full path to saved file
    """
    import os
    from datetime import datetime
    
    # Create outputs directory if it does not exist
    os.makedirs(base_dir, exist_ok=True)
    
    # Sanitize topic for filename
    safe_topic = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in topic)
    safe_topic = safe_topic.replace(" ", "_").lower()[:50]
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_format}_{safe_topic}_{timestamp}.{file_format}"
    filepath = os.path.join(base_dir, filename)
    
    # Build final content with optional evaluation header
    final_content = content
    
    if evaluation:
        eval_header = _build_evaluation_header(evaluation, file_format)
        final_content = eval_header + "\n\n" + content
    
    # Save file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    return filepath


def _build_evaluation_header(evaluation: dict, file_format: str) -> str:
    """Build evaluation metadata header based on file format"""
    
    overall_score = evaluation.get("overall", 0)
    passed = evaluation.get("passed", False)
    issues = evaluation.get("issues", [])
    
    if file_format == "md":
        # Markdown format with nice formatting
        header = "---\n"
        header += f"**Quality Evaluation:** {overall_score:.1f}/10 "
        header += "✅ PASSED" if passed else "⚠️ NEEDS REVIEW"
        header += "\n\n"
        
        if "citation_count" in evaluation:
            header += f"- **Citations Found:** {evaluation[citation_count]}\n"
        if "has_gaps" in evaluation:
            header += f"- **Clinical Gaps:** {Yes if evaluation[has_gaps] else No}\n"
        if "synthesis_length" in evaluation:
            header += f"- **Synthesis Length:** {evaluation[synthesis_length]} words\n"
        
        if issues:
            header += f"\n**Issues Identified:** {len(issues)}\n"
            for issue in issues[:3]:  # Max 3 issues
                header += f"- {issue}\n"
        
        header += "\n---"
        
    else:  # txt format
        header = "=" * 70 + "\n"
        header += f"Quality Evaluation: {overall_score:.1f}/10 "
        header += "[PASSED]" if passed else "[NEEDS REVIEW]"
        header += "\n" + "=" * 70
        
        if issues:
            header += "\nIssues: " + ", ".join(issues[:3])
        
    return header



@traceable(name="combine_results_node", run_type="chain")
async def combine_results_node(state: AgentState) -> dict:
    """Combine results from parallel PubMed and Perplexity searches."""
    pubmed_count = len(state.get("citations", []))
    perplexity_count = len(state.get("perplexity_results", []))
    return {"messages": [HumanMessage(content=f"Combined {pubmed_count + perplexity_count} sources")]}


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    graph.add_node("log_request", log_request_node)
    graph.add_node("pubmed_search", pubmed_search_node)
    graph.add_node("perplexity_search", perplexity_search_node)
    graph.add_node("validate_sources", validate_sources_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("extract_gaps", extract_gaps_node)
    graph.add_node("combine_results", combine_results_node)
    graph.add_node("finalize", finalize_node)
    
    graph.set_entry_point("log_request")
    graph.add_edge("log_request", "pubmed_search")
    graph.add_edge("log_request", "perplexity_search")
    graph.add_edge("pubmed_search", "combine_results")
    graph.add_edge("perplexity_search", "combine_results")
    graph.add_edge("combine_results", "validate_sources")
    graph.add_edge("validate_sources", "synthesize")
    graph.add_edge("synthesize", "extract_gaps")
    graph.add_edge("extract_gaps", "finalize")
    graph.add_edge("finalize", END)
    
    return graph.compile()


# =============================================================================
# LANGGRAPH CLOUD ENTRY POINT
# =============================================================================

graph = build_graph()


# =============================================================================
# LOCAL TESTING
# =============================================================================

async def run_research(
    topic: str,
    therapeutic_area: str,
    user_id: str = "anonymous",
    query_type: str = "gap_analysis",
    target_audience: str = "primary_care",
    date_range_years: int = 5,
    max_results: int = 50,
    output_format: str = "json",
    save_file: bool = True,
    file_format: str = "md",
    use_local_llm: bool = False,
    auto_evaluate: bool = False
) -> dict:
    """
    Run research workflow.
    
    Args:
        topic: Research topic
        therapeutic_area: Medical specialty
        user_id: User ID for tracking
        query_type: Type of analysis
        target_audience: Target audience for content
        date_range_years: How far back to search
        max_results: Maximum citations to retrieve
        use_local_llm: True to use Qwen3 via Ollama (free)
        auto_evaluate: True to run automated quality evaluation
        output_format: Output format (json, cme_proposal, podcast_script, gap_report, powerpoint_outline)
        save_file: Save rendered output to file (default: True)
        file_format: File extension - "md" (default) or "txt"
    
    Returns:
        Research results with optional evaluation scores
    """
    initial_state: AgentState = {
        "request_id": None,
        "user_id": user_id,
        "topic": topic,
        "therapeutic_area": therapeutic_area,
        "query_type": query_type,
        "target_audience": target_audience,
        "date_range_years": date_range_years,
        "minimum_evidence_level": EvidenceLevel.LEVEL_2B.value,
        "max_results": max_results,
        "specific_questions": [],
        "use_local_llm": use_local_llm,
        "output_format": output_format,
        "messages": [],
        "pubmed_results": [],
        "perplexity_results": [],
        "validated_citations": [],
        "synthesis": "",
        "clinical_gaps": [],
        "key_findings": [],
        "errors": [],
        "model_used": "",
        "total_tokens": 0,
        "total_cost": 0.0
    }
    
    result = await graph.ainvoke(initial_state)
    
    # Optional: Run automated evaluation
    if auto_evaluate:
        try:
            from .feedback_loop import quality_evaluator
            
            # Define expected criteria based on query type
            expected = {
                "min_citations": 3 if query_type == "podcast_content" else 5,
                "has_clinical_gaps": query_type in ["gap_analysis", "needs_assessment"],
                "has_key_findings": True,
                "synthesis_min_words": 150 if query_type == "podcast_content" else 250,
                "must_mention": [topic.split()[0]]  # At least mention main topic
            }
            
            eval_result = quality_evaluator.evaluate_result(
                result=result,
                expected=expected,
                run_id=None  # Would need to capture from LangSmith callback
            )
            
            result["_evaluation"] = eval_result
        except ImportError:
            pass  # Feedback loop module not available
    
    # Apply template rendering if requested format is not JSON
    if output_format and output_format != "json":
        try:
            try:
                from templates.renderer import render_template, TemplateType
            except (ImportError, ValueError):
                from .templates.renderer import render_template, TemplateType
            
            template_type = TemplateType(output_format)
            rendered_content = render_template(template_type, result)
            result["_output_format"] = output_format
            
            # Save to file if requested (default: True)
            if save_file:
                # Validate file_format
                if file_format not in ["md", "txt"]:
                    file_format = "md"  # Default to .md
                
                try:
                    saved_path = save_research_output(
                        content=rendered_content,
                        topic=topic,
                        output_format=output_format,
                        file_format=file_format,
                        evaluation=result.get("_evaluation")  # Include evaluation if present
                    )
                    result["_saved_file"] = saved_path
                except Exception as save_err:
                    result["_file_save_error"] = f"Failed to save file: {str(save_err)}"
                    
        except (ValueError, ImportError) as e:
            result["_rendering_error"] = f"Template rendering failed: {str(e)}"
    return result


# =============================================================================
# FEEDBACK INTEGRATION HELPERS
# =============================================================================

def get_feedback_collector():
    """Get feedback collector for manual feedback submission"""
    try:
        from .feedback_loop import feedback_collector
        return feedback_collector
    except ImportError:
        return None


def get_evaluation_dataset():
    """Get evaluation dataset for testing"""
    try:
        from .feedback_loop import evaluation_dataset
        return evaluation_dataset
    except ImportError:
        return None


def get_improvement_tracker():
    """Get improvement tracker for trend analysis"""
    try:
        from .feedback_loop import improvement_tracker
        return improvement_tracker
    except ImportError:
        return None


async def run_evaluation_suite(tags: Optional[List[str]] = None) -> dict:
    """
    Run full evaluation suite against test cases.
    
    Args:
        tags: Filter test cases by tags (e.g., ["pulmonology", "gap_analysis"])
    
    Returns:
        Evaluation results with pass/fail per case and aggregates
    """
    try:
        from .feedback_loop import quality_evaluator, evaluation_dataset
        
        return await quality_evaluator.run_evaluation_suite(
            agent_func=run_research,
            dataset=evaluation_dataset,
            tags=tags
        )
    except ImportError:
        return {"error": "Feedback loop module not available"}


if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Register with AI Factory
        print(f"Registry: {await registry.register()}")
        
        # Run with cloud LLMs + auto evaluation
        result = await run_research(
            topic="chronic cough refractory treatment",
            therapeutic_area="pulmonology",
            use_local_llm=False,  # True = Qwen3 Ollama
            auto_evaluate=True    # Run quality check
        )
        
        print(f"\n{'='*60}")
        print(f"Model: {result['model_used']}")
        print(f"Cost: ${result['total_cost']:.4f}")
        print(f"Citations: {len(result['validated_citations'])}")
        print(f"Gaps: {result['clinical_gaps']}")
        
        # Show evaluation if available
        if "_evaluation" in result:
            eval_data = result["_evaluation"]
            print(f"\n--- QUALITY EVALUATION ---")
            print(f"Overall Score: {eval_data['overall']:.2f}")
            print(f"Passed: {eval_data['passed']}")
            if eval_data['issues']:
                print(f"Issues: {eval_data['issues']}")
        
        print(f"\nSynthesis: {result['synthesis'][:500]}...")
        
        # Example: Run evaluation suite
        # print("\n--- RUNNING EVALUATION SUITE ---")
        # suite_results = await run_evaluation_suite(tags=["pulmonology"])
        # print(f"Pass rate: {suite_results['summary']['pass_rate']:.1%}")
    
    asyncio.run(main())
