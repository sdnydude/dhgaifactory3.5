"""
DHG CME Research Agent - FastAPI Server
========================================
REST API for evidence-based medical research.

Endpoints:
- POST /research - Execute research query
- GET /research/{id} - Get research results
- GET /citations/{pmid} - Get citation details
- GET /health - Health check
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import agent (handle import path)
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.research_agent import (
    CMEResearchAgent,
    ResearchResult,
    EvidenceLevel,
    THERAPEUTIC_AREAS
)

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ResearchRequest(BaseModel):
    """Request model for research endpoint"""
    topic: str = Field(..., description="Research topic", min_length=3, max_length=500)
    therapeutic_area: str = Field(..., description="Medical specialty area")
    query_type: Literal["gap_analysis", "needs_assessment", "literature_review", "podcast_content", "cme_content"] = "gap_analysis"
    target_audience: Literal["primary_care", "specialist", "np_pa", "pharmacist", "nurse", "mixed"] = "primary_care"
    date_range_years: int = Field(default=5, ge=1, le=20)
    minimum_evidence_level: Literal["1a", "1b", "2a", "2b", "3", "4", "5"] = "2b"
    max_results: int = Field(default=50, ge=10, le=200)
    specific_questions: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "topic": "chronic cough refractory treatment",
                "therapeutic_area": "pulmonology",
                "query_type": "gap_analysis",
                "target_audience": "primary_care",
                "date_range_years": 5,
                "minimum_evidence_level": "2b",
                "max_results": 50,
                "specific_questions": [
                    "What are current guideline recommendations?",
                    "What gaps exist in primary care management?"
                ]
            }
        }


class ResearchResponse(BaseModel):
    """Response model for research results"""
    research_id: str
    status: Literal["pending", "processing", "completed", "error"]
    topic: str
    therapeutic_area: str
    citation_count: int = 0
    evidence_summary: dict = {}
    clinical_gaps: List[str] = []
    key_findings: List[str] = []
    synthesis: str = ""
    citations: List[dict] = []
    metadata: dict = {}
    created_at: str
    completed_at: Optional[str] = None


class CitationResponse(BaseModel):
    """Response model for citation details"""
    pmid: Optional[str]
    doi: Optional[str]
    title: str
    authors: List[str]
    journal: str
    year: int
    evidence_level: str
    abstract: str
    url: str
    ama_citation: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    services: dict


# =============================================================================
# IN-MEMORY STORAGE (Replace with Redis/PostgreSQL in production)
# =============================================================================

research_jobs: dict[str, dict] = {}


# =============================================================================
# FASTAPI APP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("CME Research Agent starting...")
    yield
    # Shutdown
    print("CME Research Agent shutting down...")


app = FastAPI(
    title="DHG CME Research Agent",
    description="Evidence-based research API for clinical gap analysis, needs assessments, and CME content development. Only uses peer-reviewed sources.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def evidence_level_from_string(level: str) -> EvidenceLevel:
    """Convert string evidence level to enum"""
    mapping = {
        "1a": EvidenceLevel.LEVEL_1A,
        "1b": EvidenceLevel.LEVEL_1B,
        "2a": EvidenceLevel.LEVEL_2A,
        "2b": EvidenceLevel.LEVEL_2B,
        "3": EvidenceLevel.LEVEL_3,
        "4": EvidenceLevel.LEVEL_4,
        "5": EvidenceLevel.LEVEL_5,
    }
    return mapping.get(level.lower(), EvidenceLevel.LEVEL_2B)


async def execute_research(research_id: str, request: ResearchRequest):
    """Background task to execute research"""
    try:
        research_jobs[research_id]["status"] = "processing"
        
        agent = CMEResearchAgent()
        
        result = await agent.research(
            topic=request.topic,
            therapeutic_area=request.therapeutic_area,
            query_type=request.query_type,
            target_audience=request.target_audience,
            date_range_years=request.date_range_years,
            minimum_evidence_level=evidence_level_from_string(request.minimum_evidence_level),
            max_results=request.max_results,
            specific_questions=request.specific_questions or []
        )
        
        # Update job with results
        research_jobs[research_id].update({
            "status": "completed",
            "citation_count": len(result.citations),
            "evidence_summary": result.evidence_summary,
            "clinical_gaps": result.clinical_gaps,
            "key_findings": result.key_findings,
            "synthesis": result.synthesis,
            "citations": [c.to_dict() for c in result.citations],
            "metadata": result.metadata,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        research_jobs[research_id].update({
            "status": "error",
            "metadata": {"error": str(e)},
            "completed_at": datetime.now().isoformat()
        })


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    # Check API key availability
    services = {
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "google": bool(os.getenv("GOOGLE_API_KEY")),
        "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
        "pubmed": bool(os.getenv("NCBI_API_KEY")) or True  # PubMed works without key
    }
    
    all_healthy = all(services.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        services=services
    )


@app.get("/therapeutic-areas")
async def list_therapeutic_areas():
    """List supported therapeutic areas"""
    return {"therapeutic_areas": THERAPEUTIC_AREAS}


@app.post("/research", response_model=ResearchResponse)
async def create_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    sync: bool = Query(default=False, description="Wait for results (blocking)")
):
    """
    Create a new research query.
    
    By default, returns immediately with a research_id for polling.
    Set sync=true to wait for completion (may timeout for complex queries).
    """
    # Validate therapeutic area
    if request.therapeutic_area.lower() not in [ta.lower() for ta in THERAPEUTIC_AREAS]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid therapeutic area. Must be one of: {THERAPEUTIC_AREAS}"
        )
    
    research_id = str(uuid.uuid4())
    
    # Initialize job
    job = {
        "research_id": research_id,
        "status": "pending",
        "topic": request.topic,
        "therapeutic_area": request.therapeutic_area,
        "citation_count": 0,
        "evidence_summary": {},
        "clinical_gaps": [],
        "key_findings": [],
        "synthesis": "",
        "citations": [],
        "metadata": {},
        "created_at": datetime.now().isoformat(),
        "completed_at": None
    }
    research_jobs[research_id] = job
    
    if sync:
        # Execute synchronously (blocking)
        await execute_research(research_id, request)
        return ResearchResponse(**research_jobs[research_id])
    else:
        # Execute in background
        background_tasks.add_task(execute_research, research_id, request)
        return ResearchResponse(**job)


@app.get("/research/{research_id}", response_model=ResearchResponse)
async def get_research(research_id: str):
    """Get research results by ID"""
    if research_id not in research_jobs:
        raise HTTPException(status_code=404, detail="Research job not found")
    
    return ResearchResponse(**research_jobs[research_id])


@app.get("/research")
async def list_research(
    limit: int = Query(default=10, ge=1, le=100),
    status: Optional[str] = Query(default=None)
):
    """List all research jobs"""
    jobs = list(research_jobs.values())
    
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    
    # Sort by created_at descending
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"jobs": jobs[:limit], "total": len(jobs)}


@app.get("/research/{research_id}/citations")
async def get_research_citations(
    research_id: str,
    evidence_level: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Get citations for a research job with optional filtering"""
    if research_id not in research_jobs:
        raise HTTPException(status_code=404, detail="Research job not found")
    
    job = research_jobs[research_id]
    citations = job.get("citations", [])
    
    if evidence_level:
        citations = [c for c in citations if c.get("evidence_level", "").endswith(evidence_level)]
    
    return {
        "research_id": research_id,
        "total": len(citations),
        "citations": citations[:limit]
    }


@app.get("/research/{research_id}/export")
async def export_research(
    research_id: str,
    format: Literal["json", "ama_citations", "markdown"] = "json"
):
    """Export research results in various formats"""
    if research_id not in research_jobs:
        raise HTTPException(status_code=404, detail="Research job not found")
    
    job = research_jobs[research_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Research not yet completed")
    
    if format == "json":
        return JSONResponse(content=job)
    
    elif format == "ama_citations":
        # Format citations in AMA style
        citations = []
        for i, c in enumerate(job.get("citations", []), 1):
            citations.append(f"{i}. {c.get('ama_citation', c.get('title', 'Unknown'))}")
        return {"citations": "\n".join(citations)}
    
    elif format == "markdown":
        # Generate markdown report
        md = f"""# Research Report: {job['topic']}

## Overview
- **Therapeutic Area:** {job['therapeutic_area']}
- **Citations Found:** {job['citation_count']}
- **Completed:** {job.get('completed_at', 'N/A')}

## Evidence Distribution
"""
        for level, count in job.get("evidence_summary", {}).items():
            md += f"- {level}: {count}\n"
        
        md += "\n## Clinical Gaps Identified\n"
        for i, gap in enumerate(job.get("clinical_gaps", []), 1):
            md += f"{i}. {gap}\n"
        
        md += f"\n## Key Findings\n"
        for i, finding in enumerate(job.get("key_findings", []), 1):
            md += f"{i}. {finding}\n"
        
        md += f"\n## Evidence Synthesis\n{job.get('synthesis', 'N/A')}\n"
        
        md += "\n## References\n"
        for i, c in enumerate(job.get("citations", []), 1):
            md += f"{i}. {c.get('ama_citation', c.get('title', 'Unknown'))}\n"
        
        return {"markdown": md}


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An unexpected error occurred"
        }
    )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
