"""
Pydantic schemas for AI Factory Registry API
Updated for LangSmith Cloud deployment support
"""
from uuid import UUID
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class DeploymentType(str, Enum):
    LANGSMITH_CLOUD = "langsmith_cloud"
    SELF_HOSTED = "self_hosted"
    LOCAL_DEV = "local_dev"


class AgentType(str, Enum):
    RESEARCH_AGENT = "research_agent"
    CONTENT_AGENT = "content_agent"
    AUTOMATION_AGENT = "automation_agent"
    ANALYSIS_AGENT = "analysis_agent"
    ORCHESTRATOR = "orchestrator"


class Division(str, Enum):
    DHG_CME = "DHG CME"
    DHG_STUDIOS = "DHG Studios"
    DHG_AI = "DHG AI"
    DHG_PRODUCTIONS = "DHG Productions"
    STREAMCUBATION = "Streamcubation"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# =============================================================================
# SERVICE IDENTITY
# =============================================================================

class ServiceIdentity(BaseModel):
    id: str = Field(..., pattern="^[a-z0-9-]+$")
    name: str
    version: str
    division: Division
    type: AgentType
    description: Optional[str] = None
    
    # LangSmith Cloud fields
    deployment_type: DeploymentType = DeploymentType.LANGSMITH_CLOUD
    deployment_url: Optional[str] = None
    langsmith_deployment_id: Optional[str] = None
    langsmith_org: Optional[str] = None
    
    # GitHub integration
    github_repo: Optional[str] = None
    github_branch: Optional[str] = "main"
    github_path: Optional[str] = None
    
    # Legacy self-hosted fields (backward compatibility)
    endpoint: Optional[str] = None


# =============================================================================
# CAPABILITIES
# =============================================================================

class Capabilities(BaseModel):
    primary: List[str] = Field(default_factory=list)
    secondary: List[str] = Field(default_factory=list)


# =============================================================================
# I/O SCHEMA
# =============================================================================

class IOSchema(BaseModel):
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# MODEL REGISTRY
# =============================================================================

class ModelInfo(BaseModel):
    provider: str
    model_id: str
    status: str
    use_cases: List[str] = Field(default_factory=list)
    cost: Dict[str, float] = Field(default_factory=dict)
    context_window: Optional[int] = None
    max_output: Optional[int] = None
    local: bool = False
    requires: Optional[str] = None


# =============================================================================
# EXTERNAL APIS
# =============================================================================

class ExternalAPI(BaseModel):
    name: str
    type: str
    endpoint: str
    auth_required: bool = False
    rate_limit: Optional[str] = None


# =============================================================================
# OBSERVABILITY
# =============================================================================

class Observability(BaseModel):
    langsmith_project: str
    tracing: bool = True


# =============================================================================
# AGENT REGISTRATION
# =============================================================================

class AgentRegistration(BaseModel):
    service: ServiceIdentity
    capabilities: Optional[Capabilities] = None
    io_schema: Optional[IOSchema] = None
    models: Dict[str, ModelInfo] = Field(default_factory=dict)
    external_apis: List[ExternalAPI] = Field(default_factory=list)
    observability: Optional[Observability] = None


# =============================================================================
# HEARTBEAT
# =============================================================================

class HeartbeatMetrics(BaseModel):
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class Heartbeat(BaseModel):
    status: HealthStatus
    timestamp: Optional[datetime] = None
    models: Dict[str, ModelInfo] = Field(default_factory=dict)
    metrics: Optional[HeartbeatMetrics] = None
    
    # LangSmith Cloud fields
    langsmith_deployment_status: Optional[str] = None
    langsmith_traces_count: Optional[int] = None
    deployment_tier: Optional[str] = None


# =============================================================================
# API RESPONSES
# =============================================================================

class AgentResponse(BaseModel):
    id: UUID
    service: ServiceIdentity
    capabilities: Optional[Capabilities] = None
    models: Dict[str, ModelInfo] = Field(default_factory=dict)
    status: HealthStatus
    last_heartbeat: Optional[datetime] = None
    registered_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int


class ModelListResponse(BaseModel):
    models: List[Dict[str, Any]]
    total: int


class DiscoverRequest(BaseModel):
    capability: str
    prefer_local: bool = False
    max_cost: Optional[float] = None
    deployment_type: Optional[DeploymentType] = None


class DiscoverResponse(BaseModel):
    agents: List[AgentResponse]
    total: int


# =============================================================================
# ANTIGRAVITY SCHEMAS
# =============================================================================

class AntigravityChatCreate(BaseModel):
    conversation_id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    user_objective: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AntigravityChatUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    user_objective: Optional[str] = None
    message_count: Optional[int] = None
    total_tokens: Optional[int] = None
    total_cost_usd: Optional[float] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    processing_metadata: Optional[Dict[str, Any]] = None


class AntigravityChatResponse(BaseModel):
    id: UUID
    conversation_id: str
    title: Optional[str]
    summary: Optional[str]
    user_objective: Optional[str]
    created_at: datetime
    last_modified: datetime
    message_count: int
    total_tokens: int
    total_cost_usd: float
    status: str
    tags: List[str]
    file_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class AntigravityFileCreate(BaseModel):
    conversation_id: str
    file_path: str
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    artifact_type: Optional[str] = None
    summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AntigravityFileResponse(BaseModel):
    id: UUID
    conversation_id: str
    file_path: str
    file_type: Optional[str]
    file_size_bytes: Optional[int]
    artifact_type: Optional[str]
    summary: Optional[str]
    created_at: datetime
    last_modified: datetime
    
    class Config:
        from_attributes = True
# Registry Research Request Schemas
# Add to: registry/schemas.py

from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List, Dict
from datetime import datetime


# =============================================================================
# RESEARCH REQUEST SCHEMAS
# =============================================================================

class ResearchRequestInput(BaseModel):
    """Input parameters for research request"""
    topic: str
    therapeutic_area: str
    query_type: str
    target_audience: str
    date_range_from: str
    date_range_to: str
    specific_questions: Optional[List[str]] = []
    minimum_evidence_level: Optional[str] = "LEVEL_3"
    max_results: Optional[int] = 50
    use_local_llm: Optional[bool] = False
    output_format: Optional[str] = "cme_proposal"
    
    # Project details
    due_date: Optional[datetime] = None
    product_name: Optional[str] = None
    product_quantity: Optional[int] = None
    curriculum_start_date: Optional[datetime] = None
    curriculum_end_date: Optional[datetime] = None


class ResearchRequestMetadata(BaseModel):
    """Metadata about request processing"""
    model_used: Optional[str] = None
    total_tokens: Optional[int] = None
    total_cost: Optional[float] = None
    processing_time_seconds: Optional[float] = None
    pubmed_results_count: Optional[int] = None
    perplexity_results_count: Optional[int] = None


class ResearchRequestOutputSummary(BaseModel):
    """Summary of research output"""
    gaps_identified: Optional[int] = None
    key_findings_count: Optional[int] = None
    citations_count: Optional[int] = None
    evidence_levels: Optional[Dict[str, int]] = None
    output_format_used: Optional[str] = None


class ResearchRequestCreate(BaseModel):
    """Create new research request"""
    user_id: str
    agent_type: str = "cme_research"
    input_params: ResearchRequestInput


class ResearchRequestUpdate(BaseModel):
    """Update research request"""
    status: Optional[str] = None
    output_summary: Optional[ResearchRequestOutputSummary] = None
    processing_metadata: Optional[ResearchRequestMetadata] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class ResearchRequestResponse(BaseModel):
    """Research request response"""
    request_id: str
    user_id: str
    agent_type: str
    status: str
    
    input_params: ResearchRequestInput
    output_summary: Optional[ResearchRequestOutputSummary] = None
    processing_metadata: Optional[ResearchRequestMetadata] = None
    
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class ResearchRequestListResponse(BaseModel):
    """List of research requests"""
    requests: List[ResearchRequestResponse]
    total: int
    page: int
    page_size: int
