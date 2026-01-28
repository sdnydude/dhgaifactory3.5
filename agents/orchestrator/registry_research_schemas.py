# Registry Research Request Schemas
# Add to: registry/schemas.py

from pydantic import BaseModel
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
    date_range_from: datetime
    date_range_to: datetime
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
    metadata: Optional[ResearchRequestMetadata] = None
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
    metadata: Optional[ResearchRequestMetadata] = None
    
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
