"""
DHG AI FACTORY - CME PIPELINE ORCHESTRATOR (MASTER AGENT)
Main FastAPI application for coordinating all CME and NON-CME content generation
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
import httpx
import os
import structlog
from datetime import datetime
import uuid

# Initialize structured logging
logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="DHG AI Factory - CME Orchestrator",
    description="Master Agent for CME/NON-CME Content Pipeline",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# WEBSOCKETS
# ============================================================================
from websocket_manager import manager as ws_manager

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, client_id: str | None = None):
    client_id = await ws_manager.connect(websocket, client_id)
    try:
        while True:
            msg = await websocket.receive_json()
            resp = await ws_manager.handle_client_message(client_id, msg)
            if resp:
                await ws_manager.send_message(client_id, resp)
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
    except Exception as e:
        logger.error("ws_error", client_id=client_id, error=str(e))
        ws_manager.disconnect(client_id)


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """System configuration from environment variables"""
    REGISTRY_DB_URL = os.getenv("REGISTRY_DB_URL")
    CME_MODE_DEFAULT = os.getenv("CME_MODE_DEFAULT", "auto")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Agent endpoints
    MEDICAL_LLM_URL = "http://medical-llm:8000"
    RESEARCH_URL = "http://research:8000"
    CURRICULUM_URL = "http://curriculum:8000"
    OUTCOMES_URL = "http://outcomes:8000"
    COMPETITOR_INTEL_URL = "http://competitor-intel:8000"
    QA_COMPLIANCE_URL = "http://qa-compliance:8000"
    
    # CME Configuration
    ACCME_STRICT_MODE = os.getenv("ACCME_STRICT_MODE", "true").lower() == "true"
    MOORE_LEVELS_VALIDATION = os.getenv("MOORE_LEVELS_VALIDATION", "true").lower() == "true"
    FAIR_BALANCE_CHECK = os.getenv("FAIR_BALANCE_CHECK", "true").lower() == "true"

config = Config()

# ============================================================================
# ENUMS AND MODELS
# ============================================================================

class ComplianceMode(str, Enum):
    """Content compliance mode"""
    CME = "cme"
    NON_CME = "non-cme"
    AUTO = "auto"

class TaskType(str, Enum):
    """Types of tasks the orchestrator can handle"""
    NEEDS_ASSESSMENT = "needs_assessment"
    CURRICULUM = "curriculum"
    LEARNING_OBJECTIVES = "learning_objectives"
    CME_SCRIPT = "cme_script"
    GRANT_REQUEST = "grant_request"
    GAP_ANALYSIS = "gap_analysis"
    OUTCOMES_PLAN = "outcomes_plan"
    BUSINESS_STRATEGY = "business_strategy"
    COMPETITOR_ANALYSIS = "competitor_analysis"

class MooreLevels(str, Enum):
    """Moore's Levels for CME Outcomes"""
    LEVEL_1 = "participation"
    LEVEL_2 = "satisfaction"
    LEVEL_3 = "learning_declarative"
    LEVEL_4 = "competence"
    LEVEL_5 = "performance"
    LEVEL_6 = "patient_health"
    LEVEL_7 = "community_health"

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TaskRequest(BaseModel):
    """Request model for orchestrator tasks"""
    task_type: TaskType
    topic: str
    compliance_mode: ComplianceMode = Field(default=ComplianceMode.AUTO)
    target_audience: Optional[str] = None
    funder: Optional[str] = None
    word_count_target: Optional[int] = None
    moore_levels: Optional[List[MooreLevels]] = None
    include_sdoh: bool = True
    include_equity: bool = True
    reference_count_min: int = 6
    reference_count_max: int = 12
    additional_context: Optional[Dict[str, Any]] = None
    force_mode: Optional[ComplianceMode] = None

class TaskResponse(BaseModel):
    """Response model for orchestrator tasks"""
    task_id: str
    status: str
    compliance_mode: ComplianceMode
    deliverables: Optional[Dict[str, Any]] = None
    violations: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    agents: Dict[str, str]
    registry_connected: bool

# ============================================================================
# AGENT CLIENT
# ============================================================================

class AgentClient:
    """HTTP client for communicating with specialized agents"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def call_agent(self, url: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specialized agent"""
        try:
            response = await self.client.post(f"{url}/{endpoint}", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("agent_call_failed", url=url, endpoint=endpoint, error=str(e))
            raise HTTPException(status_code=502, detail=f"Agent call failed: {str(e)}")
    
    async def health_check(self, url: str) -> bool:
        """Check if an agent is healthy"""
        try:
            response = await self.client.get(f"{url}/health", timeout=5.0)
            return response.status_code == 200
        except:
            return False

agent_client = AgentClient()

# ============================================================================
# COMPLIANCE MODE DETECTION
# ============================================================================

def detect_compliance_mode(request: TaskRequest) -> ComplianceMode:
    """
    Detect whether request requires CME or NON-CME mode
    
    CME triggers:
    - Explicit keywords: CME, ACCME, needs assessment, Moore Levels, etc.
    - Task types: needs_assessment, curriculum, learning_objectives, etc.
    
    NON-CME triggers:
    - Explicit: "This is not CME content", "Use NON-CME Mode"
    - Task types: business_strategy, competitor_analysis
    
    User override: force_mode parameter
    """
    # User override
    if request.force_mode:
        return request.force_mode
    
    # Explicit mode
    if request.compliance_mode != ComplianceMode.AUTO:
        return request.compliance_mode
    
    # CME task types
    cme_tasks = [
        TaskType.NEEDS_ASSESSMENT,
        TaskType.CURRICULUM,
        TaskType.LEARNING_OBJECTIVES,
        TaskType.CME_SCRIPT,
        TaskType.GRANT_REQUEST,
        TaskType.GAP_ANALYSIS,
        TaskType.OUTCOMES_PLAN,
    ]
    
    if request.task_type in cme_tasks:
        return ComplianceMode.CME
    
    # NON-CME task types
    non_cme_tasks = [
        TaskType.BUSINESS_STRATEGY,
        TaskType.COMPETITOR_ANALYSIS,
    ]
    
    if request.task_type in non_cme_tasks:
        return ComplianceMode.NON_CME
    
    # CME keywords in topic
    cme_keywords = [
        "cme", "accme", "needs assessment", "moore levels",
        "gap analysis", "learning objectives", "curriculum",
        "educational", "medical education", "continuing education"
    ]
    
    topic_lower = request.topic.lower()
    if any(keyword in topic_lower for keyword in cme_keywords):
        return ComplianceMode.CME
    
    # NON-CME keywords
    non_cme_keywords = [
        "not cme", "non-cme", "business", "strategy",
        "commercial", "marketing", "competitive"
    ]
    
    if any(keyword in topic_lower for keyword in non_cme_keywords):
        return ComplianceMode.NON_CME
    
    # Default to CME (conservative approach)
    return ComplianceMode.CME

# ============================================================================
# ORCHESTRATION LOGIC
# ============================================================================

async def orchestrate_needs_assessment(
    request: TaskRequest,
    compliance_mode: ComplianceMode,
    task_id: str
) -> Dict[str, Any]:
    """Orchestrate generation of a CME Needs Assessment"""
    
    logger.info("orchestrating_needs_assessment", task_id=task_id, topic=request.topic)
    
    # Step 1: Research Agent - gather evidence
    research_payload = {
        "topic": request.topic,
        "sources": [
            "pubmed",
            "clinical_trials",
            "cdc_wonder",
            "cms_quality",
            "uspstf",
            "consensus"
        ],
        "max_results": 50,
        "include_epidemiology": True,
        "include_guidelines": True,
        "include_quality_measures": True,
    }
    
    research_results = await agent_client.call_agent(
        config.RESEARCH_URL,
        "research",
        research_payload
    )
    
    # Step 2: Medical LLM Agent - generate assessment
    medical_llm_payload = {
        "task": "needs_assessment",
        "topic": request.topic,
        "research_data": research_results,
        "compliance_mode": compliance_mode.value,
        "word_count_target": request.word_count_target or 1250,
        "include_sdoh": request.include_sdoh,
        "include_equity": request.include_equity,
        "reference_count_min": request.reference_count_min,
        "reference_count_max": request.reference_count_max,
        "style": "cleo_abram_narrative",
        "structure": "scr_framework"  # Situation-Complication-Resolution
    }
    
    assessment_draft = await agent_client.call_agent(
        config.MEDICAL_LLM_URL,
        "generate",
        medical_llm_payload
    )
    
    # Step 3: QA/Compliance Agent - validate
    qa_payload = {
        "content": assessment_draft["content"],
        "compliance_mode": compliance_mode.value,
        "document_type": "needs_assessment",
        "checks": [
            "accme_compliance",
            "fair_balance",
            "commercial_bias",
            "reference_validation",
            "word_count",
            "sdoh_equity"
        ]
    }
    
    qa_results = await agent_client.call_agent(
        config.QA_COMPLIANCE_URL,
        "validate",
        qa_payload
    )
    
    # Step 4: If violations, retry with corrections
    if qa_results.get("violations"):
        logger.warning("qa_violations_detected", violations=qa_results["violations"])
        
        # Request corrections
        medical_llm_payload["corrections"] = qa_results["violations"]
        assessment_draft = await agent_client.call_agent(
            config.MEDICAL_LLM_URL,
            "generate",
            medical_llm_payload
        )
        
        # Re-validate
        qa_payload["content"] = assessment_draft["content"]
        qa_results = await agent_client.call_agent(
            config.QA_COMPLIANCE_URL,
            "validate",
            qa_payload
        )
    
    # Return deliverables
    return {
        "needs_assessment": assessment_draft["content"],
        "references": assessment_draft["references"],
        "research_summary": research_results.get("summary"),
        "qa_report": qa_results,
        "metadata": {
            "word_count": len(assessment_draft["content"].split()),
            "reference_count": len(assessment_draft["references"]),
            "compliance_mode": compliance_mode.value,
            "sources_used": research_results.get("sources_used", [])
        }
    }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    agents_status = {}
    
    # Check all agent health
    for name, url in [
        ("medical-llm", config.MEDICAL_LLM_URL),
        ("research", config.RESEARCH_URL),
        ("curriculum", config.CURRICULUM_URL),
        ("outcomes", config.OUTCOMES_URL),
        ("competitor-intel", config.COMPETITOR_INTEL_URL),
        ("qa-compliance", config.QA_COMPLIANCE_URL),
    ]:
        agents_status[name] = "healthy" if await agent_client.health_check(url) else "unhealthy"
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        agents=agents_status,
        registry_connected=bool(config.REGISTRY_DB_URL)
    )

@app.post("/orchestrate", response_model=TaskResponse)
async def orchestrate_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Main orchestration endpoint
    
    Detects compliance mode, coordinates specialized agents,
    and returns completed deliverables
    """
    task_id = str(uuid.uuid4())
    
    logger.info(
        "task_received",
        task_id=task_id,
        task_type=request.task_type,
        topic=request.topic
    )
    
    # Detect compliance mode
    compliance_mode = detect_compliance_mode(request)
    logger.info("compliance_mode_detected", task_id=task_id, mode=compliance_mode.value)
    
    # Route to appropriate orchestration logic
    try:
        if request.task_type == TaskType.NEEDS_ASSESSMENT:
            deliverables = await orchestrate_needs_assessment(request, compliance_mode, task_id)
        else:
            raise HTTPException(
                status_code=501,
                detail=f"Task type {request.task_type} not yet implemented"
            )
        
        # Log to registry (background task)
        # TODO: Implement registry logging
        
        return TaskResponse(
            task_id=task_id,
            status="completed",
            compliance_mode=compliance_mode,
            deliverables=deliverables,
            violations=deliverables.get("qa_report", {}).get("violations"),
            warnings=deliverables.get("qa_report", {}).get("warnings"),
            metadata={
                "completed_at": datetime.utcnow().isoformat(),
                "task_type": request.task_type.value,
            }
        )
        
    except Exception as e:
        logger.error("orchestration_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "DHG AI Factory - CME Orchestrator",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs"
    }

# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info("orchestrator_starting", config=config.__dict__)
    
    # Dependency Injection for WebSocket Manager
    ws_manager.agent_client = agent_client

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    await agent_client.client.aclose()
    logger.info("orchestrator_shutdown")
