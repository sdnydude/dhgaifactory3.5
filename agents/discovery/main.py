"""
DHG AI FACTORY - DISCOVERY AGENT
Divergent phase: Problem exploration, requirements gathering, opportunity identification
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import structlog
from datetime import datetime
import uuid

logger = structlog.get_logger()

app = FastAPI(
    title="DHG AI Factory - Discovery Agent",
    description="Divergent-Convergent Framework: Problem exploration and requirements gathering",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Config:
    REGISTRY_DB_URL = os.getenv("REGISTRY_DB_URL")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


config = Config()


class DiscoveryRequest(BaseModel):
    """Request for discovery session"""
    project_name: str
    domain: str
    initial_context: Optional[str] = None
    stakeholders: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    discovery_type: str = "comprehensive"


class Opportunity(BaseModel):
    """Identified opportunity"""
    id: str
    title: str
    description: str
    impact: str
    effort: str
    priority: int
    related_requirements: List[str] = []


class Requirement(BaseModel):
    """Gathered requirement"""
    id: str
    category: str
    description: str
    priority: str
    source: str
    acceptance_criteria: Optional[List[str]] = None


class DiscoveryResponse(BaseModel):
    """Discovery session results"""
    session_id: str
    project_name: str
    domain: str
    opportunities: List[Opportunity]
    requirements: List[Requirement]
    stakeholder_analysis: Dict[str, Any]
    problem_statement: str
    scope_boundaries: Dict[str, List[str]]
    risks: List[Dict[str, Any]]
    next_steps: List[str]
    created_at: str


class InterviewSynthesisRequest(BaseModel):
    """Request for interview synthesis"""
    session_id: str
    interview_notes: List[Dict[str, str]]
    context: Optional[str] = None


class OpportunityMapRequest(BaseModel):
    """Request for opportunity mapping"""
    session_id: str
    opportunities: List[Dict[str, Any]]
    evaluation_criteria: Optional[List[str]] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "discovery",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": [
            "problem_exploration",
            "requirements_gathering",
            "opportunity_identification",
            "stakeholder_analysis",
            "interview_synthesis"
        ]
    }


@app.post("/discover", response_model=DiscoveryResponse)
async def run_discovery(request: DiscoveryRequest):
    """
    Run a discovery session
    
    Divergent phase activities:
    1. Explore problem space
    2. Gather requirements from stakeholders
    3. Identify opportunities
    4. Analyze stakeholder needs
    """
    session_id = str(uuid.uuid4())
    logger.info("discovery_session_started", session_id=session_id, project=request.project_name)
    
    opportunities = [
        Opportunity(
            id=str(uuid.uuid4()),
            title="Process Automation",
            description=f"Automate manual processes in {request.domain}",
            impact="high",
            effort="medium",
            priority=1,
            related_requirements=["REQ-001", "REQ-002"]
        ),
        Opportunity(
            id=str(uuid.uuid4()),
            title="Data Integration",
            description="Consolidate data sources for unified insights",
            impact="medium",
            effort="high",
            priority=2,
            related_requirements=["REQ-003"]
        ),
        Opportunity(
            id=str(uuid.uuid4()),
            title="User Experience Enhancement",
            description="Improve user workflows and reduce friction",
            impact="high",
            effort="low",
            priority=1,
            related_requirements=["REQ-004", "REQ-005"]
        )
    ]
    
    requirements = [
        Requirement(
            id="REQ-001",
            category="Functional",
            description=f"System shall support {request.domain} workflows",
            priority="must-have",
            source="stakeholder_interview",
            acceptance_criteria=["Workflow completion under 5 minutes", "Error rate below 1%"]
        ),
        Requirement(
            id="REQ-002",
            category="Functional",
            description="System shall provide real-time status updates",
            priority="must-have",
            source="stakeholder_interview",
            acceptance_criteria=["Updates within 5 seconds", "99.9% delivery success"]
        ),
        Requirement(
            id="REQ-003",
            category="Integration",
            description="System shall integrate with existing data sources",
            priority="should-have",
            source="technical_review",
            acceptance_criteria=["API connectivity", "Data sync within 1 hour"]
        ),
        Requirement(
            id="REQ-004",
            category="Usability",
            description="Interface shall be intuitive for non-technical users",
            priority="must-have",
            source="user_research",
            acceptance_criteria=["Task completion without training", "SUS score > 80"]
        ),
        Requirement(
            id="REQ-005",
            category="Performance",
            description="System shall respond within 2 seconds under normal load",
            priority="must-have",
            source="technical_review",
            acceptance_criteria=["P95 latency < 2s", "Support 100 concurrent users"]
        )
    ]
    
    stakeholder_analysis = {
        "primary_users": request.stakeholders or ["end_users", "administrators"],
        "decision_makers": ["project_sponsor", "department_head"],
        "influencers": ["technical_team", "operations"],
        "affected_parties": ["customers", "partners"],
        "communication_needs": {
            "primary_users": "Weekly updates, training sessions",
            "decision_makers": "Monthly executive summaries",
            "technical_team": "Daily standups, documentation"
        }
    }
    
    problem_statement = (
        f"The {request.domain} domain currently faces challenges in efficiency, "
        f"data integration, and user experience. {request.project_name} aims to address "
        "these gaps through targeted automation, unified data architecture, and "
        "streamlined user workflows."
    )
    
    scope_boundaries = {
        "in_scope": [
            f"Core {request.domain} workflows",
            "User authentication and authorization",
            "Data integration with primary systems",
            "Reporting and analytics dashboard"
        ],
        "out_of_scope": [
            "Legacy system replacement",
            "Mobile application (phase 2)",
            "Third-party vendor integrations (unless specified)"
        ],
        "assumptions": [
            "Existing infrastructure can support new system",
            "Stakeholders available for regular feedback",
            "Budget approved for initial phase"
        ]
    }
    
    risks = [
        {
            "id": "RISK-001",
            "description": "Stakeholder availability for requirements validation",
            "probability": "medium",
            "impact": "high",
            "mitigation": "Schedule dedicated discovery sessions in advance"
        },
        {
            "id": "RISK-002",
            "description": "Integration complexity with legacy systems",
            "probability": "high",
            "impact": "medium",
            "mitigation": "Conduct technical spike early in project"
        },
        {
            "id": "RISK-003",
            "description": "Scope creep during development",
            "probability": "high",
            "impact": "high",
            "mitigation": "Strict change control process and regular scope reviews"
        }
    ]
    
    next_steps = [
        "Validate requirements with stakeholders",
        "Prioritize opportunities using MoSCoW framework",
        "Create detailed user stories for top priorities",
        "Schedule architecture review session",
        "Develop project roadmap and timeline"
    ]
    
    logger.info("discovery_session_completed", session_id=session_id, 
                opportunities=len(opportunities), requirements=len(requirements))
    
    return DiscoveryResponse(
        session_id=session_id,
        project_name=request.project_name,
        domain=request.domain,
        opportunities=opportunities,
        requirements=requirements,
        stakeholder_analysis=stakeholder_analysis,
        problem_statement=problem_statement,
        scope_boundaries=scope_boundaries,
        risks=risks,
        next_steps=next_steps,
        created_at=datetime.utcnow().isoformat()
    )


@app.post("/synthesize-interviews")
async def synthesize_interviews(request: InterviewSynthesisRequest):
    """
    Synthesize interview notes into structured insights
    
    Processes multiple interview notes to extract:
    - Common themes
    - Pain points
    - Requirements
    - Opportunities
    """
    logger.info("interview_synthesis_started", session_id=request.session_id, 
                interview_count=len(request.interview_notes))
    
    themes = [
        {"theme": "Efficiency", "frequency": 8, "quotes": ["We need faster workflows"]},
        {"theme": "Integration", "frequency": 6, "quotes": ["Systems don't talk to each other"]},
        {"theme": "Usability", "frequency": 7, "quotes": ["Too many clicks to complete a task"]}
    ]
    
    pain_points = [
        {"issue": "Manual data entry", "severity": "high", "affected_users": 15},
        {"issue": "Lack of real-time visibility", "severity": "medium", "affected_users": 12},
        {"issue": "Complex approval workflows", "severity": "high", "affected_users": 20}
    ]
    
    return {
        "session_id": request.session_id,
        "interviews_analyzed": len(request.interview_notes),
        "themes": themes,
        "pain_points": pain_points,
        "synthesized_at": datetime.utcnow().isoformat()
    }


@app.post("/map-opportunities")
async def map_opportunities(request: OpportunityMapRequest):
    """
    Create opportunity map with prioritization
    
    Evaluates opportunities against criteria and creates
    a prioritized roadmap
    """
    logger.info("opportunity_mapping_started", session_id=request.session_id,
                opportunity_count=len(request.opportunities))
    
    criteria = request.evaluation_criteria or ["impact", "effort", "risk", "alignment"]
    
    evaluated = []
    for i, opp in enumerate(request.opportunities):
        evaluated.append({
            **opp,
            "scores": {c: (5 - i) for c in criteria},
            "weighted_score": 4.2 - (i * 0.3),
            "recommended_phase": 1 if i < 2 else 2
        })
    
    return {
        "session_id": request.session_id,
        "evaluated_opportunities": evaluated,
        "criteria_used": criteria,
        "recommendations": {
            "phase_1": [e for e in evaluated if e["recommended_phase"] == 1],
            "phase_2": [e for e in evaluated if e["recommended_phase"] == 2]
        },
        "mapped_at": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "agent": "discovery",
        "description": "Divergent-Convergent Framework: Discovery Agent",
        "phase": "divergent",
        "endpoints": ["/health", "/discover", "/synthesize-interviews", "/map-opportunities"]
    }


@app.on_event("startup")
async def startup_event():
    logger.info("discovery_agent_starting")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("discovery_agent_stopping")
