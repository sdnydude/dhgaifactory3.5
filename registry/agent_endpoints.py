
"""
Agent Registry Endpoints for AI Factory
Handles agent registration, heartbeats, discovery, and model tracking
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

# Import get_db from main API
from database import get_db


import agent_service as svc
from schemas import (
    AgentRegistration, Heartbeat, AgentResponse, AgentListResponse,
    ModelListResponse, DiscoverRequest, DiscoverResponse,
    HealthStatus
)


router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def _agent_response(agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id, service=agent, capabilities=agent.capabilities,
        models=agent.models or {}, status=HealthStatus(agent.status),
        last_heartbeat=agent.last_heartbeat, registered_at=agent.registered_at,
        updated_at=agent.updated_at,
    )


# =============================================================================
# AGENT REGISTRATION
# =============================================================================

@router.post("/register", response_model=dict, status_code=status.HTTP_200_OK)
async def register_agent(registration: AgentRegistration, db: Session = Depends(get_db)):
    """Register a new agent or update existing registration."""
    agent_id, action = svc.register_or_update_agent(db, registration)
    if action == "updated":
        return {"status": "updated", "agent_id": agent_id, "message": f"Agent {agent_id} registration updated"}
    return {"status": "registered", "agent_id": agent_id, "message": f"Agent {agent_id} registered successfully"}


# =============================================================================
# HEARTBEAT
# =============================================================================

@router.post("/{service_id}/heartbeat", response_model=dict)
async def agent_heartbeat(service_id: str, heartbeat: Heartbeat, db: Session = Depends(get_db)):
    """Receive heartbeat from agent with current status and metrics."""
    hb_record = svc.record_heartbeat(db, service_id, heartbeat)
    if not hb_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {service_id} not found. Please register first."
        )
    return {"status": "received", "agent_id": service_id, "timestamp": hb_record.timestamp.isoformat()}


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
    """List all registered agents with optional filtering."""
    agents = svc.list_agents(
        db, division=division, agent_type=type,
        deployment_type=deployment_type, status=status,
    )
    agent_responses = [_agent_response(a) for a in agents]
    return AgentListResponse(agents=agent_responses, total=len(agent_responses))


# =============================================================================
# GET AGENT
# =============================================================================

@router.get("/{service_id}", response_model=AgentResponse)
async def get_agent(service_id: str, db: Session = Depends(get_db)):
    """Get details for a specific agent."""
    agent = svc.get_agent(db, service_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {service_id} not found")
    return _agent_response(agent)


# =============================================================================
# DELETE AGENT
# =============================================================================

@router.delete("/{service_id}", response_model=dict)
async def deregister_agent(service_id: str, db: Session = Depends(get_db)):
    """Deregister an agent from the registry."""
    agent = svc.deregister_agent(db, service_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {service_id} not found")
    return {"status": "deregistered", "agent_id": service_id, "message": f"Agent {service_id} deregistered successfully"}


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
    """List all available models across all agents."""
    all_models = svc.list_models(db, provider=provider, local=local, model_status=status)
    return ModelListResponse(models=all_models, total=len(all_models))


# =============================================================================
# DISCOVER AGENTS
# =============================================================================

@router.post("/discover", response_model=DiscoverResponse)
async def discover_agents(request: DiscoverRequest, db: Session = Depends(get_db)):
    """Discover agents by capability, with optional filters for cost and deployment type."""
    deployment_type_val = request.deployment_type.value if request.deployment_type else None
    agents = svc.discover_agents(
        db, request.capability,
        deployment_type=deployment_type_val,
        max_cost=request.max_cost,
        prefer_local=request.prefer_local,
    )
    agent_responses = [_agent_response(a) for a in agents]
    return DiscoverResponse(agents=agent_responses, total=len(agent_responses))
