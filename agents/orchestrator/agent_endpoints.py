
"""
Agent Registry Endpoints for AI Factory
Handles agent registration, heartbeats, discovery, and model tracking
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

# Import get_db from main API
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db

from sqlalchemy import func, or_

from models import Agent, AgentHeartbeat
from schemas import (
    AgentRegistration, Heartbeat, AgentResponse, AgentListResponse,
    ModelListResponse, DiscoverRequest, DiscoverResponse,
    DeploymentType, AgentType, Division, HealthStatus
)


router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


# =============================================================================
# AGENT REGISTRATION
# =============================================================================

@router.post("/register", response_model=dict, status_code=status.HTTP_200_OK)
async def register_agent(registration: AgentRegistration, db: Session = Depends(get_db)):
    """
    Register a new agent or update existing registration.
    
    Supports both LangSmith Cloud and self-hosted agents.
    """
    agent_id = registration.service.id
    
    # Check if agent already exists
    existing = db.query(Agent).filter(Agent.id == agent_id).first()
    
    if existing:
        # Update existing registration
        existing.name = registration.service.name
        existing.version = registration.service.version
        existing.division = registration.service.division.value
        existing.type = registration.service.type.value
        existing.description = registration.service.description
        existing.deployment_type = registration.service.deployment_type.value
        existing.deployment_url = registration.service.deployment_url
        existing.langsmith_deployment_id = registration.service.langsmith_deployment_id
        existing.langsmith_org = registration.service.langsmith_org
        existing.github_repo = registration.service.github_repo
        existing.github_branch = registration.service.github_branch
        existing.github_path = registration.service.github_path
        existing.endpoint = registration.service.endpoint
        existing.capabilities = registration.capabilities.dict() if registration.capabilities else None
        existing.io_schema = registration.io_schema.dict() if registration.io_schema else None
        existing.models = {k: v.dict() for k, v in registration.models.items()}
        existing.external_apis = [api.dict() for api in registration.external_apis]
        existing.observability = registration.observability.dict() if registration.observability else None
        existing.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing)
        
        return {
            "status": "updated",
            "agent_id": agent_id,
            "message": f"Agent {agent_id} registration updated"
        }
    else:
        # Create new agent
        new_agent = Agent(
            id=agent_id,
            name=registration.service.name,
            version=registration.service.version,
            division=registration.service.division.value,
            type=registration.service.type.value,
            description=registration.service.description,
            deployment_type=registration.service.deployment_type.value,
            deployment_url=registration.service.deployment_url,
            langsmith_deployment_id=registration.service.langsmith_deployment_id,
            langsmith_org=registration.service.langsmith_org,
            github_repo=registration.service.github_repo,
            github_branch=registration.service.github_branch,
            github_path=registration.service.github_path,
            endpoint=registration.service.endpoint,
            capabilities=registration.capabilities.dict() if registration.capabilities else None,
            io_schema=registration.io_schema.dict() if registration.io_schema else None,
            models={k: v.dict() for k, v in registration.models.items()},
            external_apis=[api.dict() for api in registration.external_apis],
            observability=registration.observability.dict() if registration.observability else None,
            status="healthy"
        )
        
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        
        return {
            "status": "registered",
            "agent_id": agent_id,
            "message": f"Agent {agent_id} registered successfully"
        }


# =============================================================================
# HEARTBEAT
# =============================================================================

@router.post("/{service_id}/heartbeat", response_model=dict)
async def agent_heartbeat(service_id: str, heartbeat: Heartbeat, db: Session = Depends(get_db)):
    """
    Receive heartbeat from agent with current status and metrics.
    """
    agent = db.query(Agent).filter(Agent.id == service_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {service_id} not found. Please register first."
        )
    
    # Update agent status and last heartbeat
    agent.status = heartbeat.status.value
    agent.last_heartbeat = datetime.utcnow()
    
    # Create heartbeat record
    hb_record = AgentHeartbeat(
        agent_id=service_id,
        status=heartbeat.status.value,
        timestamp=heartbeat.timestamp or datetime.utcnow(),
        models={k: v.dict() for k, v in heartbeat.models.items()} if heartbeat.models else None,
        requests_total=heartbeat.metrics.requests_total if heartbeat.metrics else 0,
        requests_success=heartbeat.metrics.requests_success if heartbeat.metrics else 0,
        requests_failed=heartbeat.metrics.requests_failed if heartbeat.metrics else 0,
        avg_latency_ms=heartbeat.metrics.avg_latency_ms if heartbeat.metrics else 0.0,
        total_tokens=heartbeat.metrics.total_tokens if heartbeat.metrics else 0,
        total_cost_usd=heartbeat.metrics.total_cost_usd if heartbeat.metrics else 0.0,
        langsmith_deployment_status=heartbeat.langsmith_deployment_status,
        langsmith_traces_count=heartbeat.langsmith_traces_count,
        deployment_tier=heartbeat.deployment_tier
    )
    
    db.add(hb_record)
    db.commit()
    
    return {
        "status": "received",
        "agent_id": service_id,
        "timestamp": hb_record.timestamp.isoformat()
    }


# =============================================================================
# LIST AGENTS
# =============================================================================

@router.get("", response_model=AgentListResponse)
async def list_agents(
    division: Optional[str] = None,
    type: Optional[str] = None,
    deployment_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all registered agents with optional filtering.
    """
    query = db.query(Agent)
    
    if division:
        query = query.filter(Agent.division == division)
    if type:
        query = query.filter(Agent.type == type)
    if deployment_type:
        query = query.filter(Agent.deployment_type == deployment_type)
    if status:
        query = query.filter(Agent.status == status)
    
    agents = query.all()
    
    agent_responses = [
        AgentResponse(
            id=agent.id,
            service=agent,
            capabilities=agent.capabilities,
            models=agent.models or {},
            status=HealthStatus(agent.status),
            last_heartbeat=agent.last_heartbeat,
            registered_at=agent.registered_at,
            updated_at=agent.updated_at
        )
        for agent in agents
    ]
    
    return AgentListResponse(agents=agent_responses, total=len(agent_responses))


# =============================================================================
# GET AGENT
# =============================================================================

@router.get("/{service_id}", response_model=AgentResponse)
async def get_agent(service_id: str, db: Session = Depends(get_db)):
    """
    Get details for a specific agent.
    """
    agent = db.query(Agent).filter(Agent.id == service_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {service_id} not found"
        )
    
    return AgentResponse(
        id=agent.id,
        service=agent,
        capabilities=agent.capabilities,
        models=agent.models or {},
        status=HealthStatus(agent.status),
        last_heartbeat=agent.last_heartbeat,
        registered_at=agent.registered_at,
        updated_at=agent.updated_at
    )


# =============================================================================
# DELETE AGENT
# =============================================================================

@router.delete("/{service_id}", response_model=dict)
async def deregister_agent(service_id: str, db: Session = Depends(get_db)):
    """
    Deregister an agent from the registry.
    """
    agent = db.query(Agent).filter(Agent.id == service_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {service_id} not found"
        )
    
    db.delete(agent)
    db.commit()
    
    return {
        "status": "deregistered",
        "agent_id": service_id,
        "message": f"Agent {service_id} deregistered successfully"
    }


# =============================================================================
# LIST MODELS
# =============================================================================

@router.get("/models/list", response_model=ModelListResponse)
async def list_models(
    provider: Optional[str] = None,
    local: Optional[bool] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all available models across all agents.
    """
    agents = db.query(Agent).filter(Agent.status == "healthy").all()
    
    all_models = []
    for agent in agents:
        if not agent.models:
            continue
            
        for model_name, model_info in agent.models.items():
            # Apply filters
            if provider and model_info.get("provider") != provider:
                continue
            if local is not None and model_info.get("local", False) != local:
                continue
            if status and model_info.get("status") != status:
                continue
            
            all_models.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "model_name": model_name,
                **model_info
            })
    
    return ModelListResponse(models=all_models, total=len(all_models))


# =============================================================================
# DISCOVER AGENTS
# =============================================================================

@router.post("/discover", response_model=DiscoverResponse)
async def discover_agents(request: DiscoverRequest, db: Session = Depends(get_db)):
    """
    Discover agents by capability, with optional filters for cost and deployment type.
    """
    query = db.query(Agent).filter(Agent.status == "healthy")
    
    # Filter by deployment type if specified
    if request.deployment_type:
        query = query.filter(Agent.deployment_type == request.deployment_type.value)
    
    agents = query.all()
    
    matching_agents = []
    for agent in agents:
        if not agent.capabilities:
            continue
        
        # Check if agent has the requested capability
        all_capabilities = (
            agent.capabilities.get("primary", []) +
            agent.capabilities.get("secondary", [])
        )
        
        if request.capability not in all_capabilities:
            continue
        
        # Filter by cost if specified
        if request.max_cost is not None and agent.models:
            # Check if agent has models within cost limit
            has_affordable_model = False
            for model_info in agent.models.values():
                if request.prefer_local and model_info.get("local", False):
                    has_affordable_model = True
                    break
                cost = model_info.get("cost", {})
                avg_cost = (cost.get("input", 0) + cost.get("output", 0)) / 2
                if avg_cost <= request.max_cost:
                    has_affordable_model = True
                    break
            
            if not has_affordable_model:
                continue
        
        matching_agents.append(
            AgentResponse(
                id=agent.id,
                service=agent,
                capabilities=agent.capabilities,
                models=agent.models or {},
                status=HealthStatus(agent.status),
                last_heartbeat=agent.last_heartbeat,
                registered_at=agent.registered_at,
                updated_at=agent.updated_at
            )
        )
    
    return DiscoverResponse(agents=matching_agents, total=len(matching_agents))
