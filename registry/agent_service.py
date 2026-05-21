"""Agent registry service — DB operations for agent registration, heartbeats, discovery."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models import Agent, AgentHeartbeat


def register_or_update_agent(db: Session, registration) -> tuple[str, str]:
    """Register a new agent or update existing. Returns (agent_id, 'registered'|'updated')."""
    agent_id = registration.service.id

    existing = db.query(Agent).filter(Agent.id == agent_id).first()

    if existing:
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
        return agent_id, "updated"
    else:
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
            status="healthy",
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        return agent_id, "registered"


def record_heartbeat(db: Session, service_id: str, heartbeat) -> AgentHeartbeat | None:
    """Record heartbeat and update agent status. Returns None if agent not found."""
    agent = db.query(Agent).filter(Agent.id == service_id).first()
    if not agent:
        return None

    agent.status = heartbeat.status.value
    agent.last_heartbeat = datetime.utcnow()

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
        deployment_tier=heartbeat.deployment_tier,
    )
    db.add(hb_record)
    db.commit()
    return hb_record


def list_agents(
    db: Session,
    *,
    division: str | None = None,
    agent_type: str | None = None,
    deployment_type: str | None = None,
    status: str | None = None,
) -> list[Agent]:
    query = db.query(Agent)
    if division:
        query = query.filter(Agent.division == division)
    if agent_type:
        query = query.filter(Agent.type == agent_type)
    if deployment_type:
        query = query.filter(Agent.deployment_type == deployment_type)
    if status:
        query = query.filter(Agent.status == status)
    return query.all()


def get_agent(db: Session, service_id: str) -> Agent | None:
    return db.query(Agent).filter(Agent.id == service_id).first()


def deregister_agent(db: Session, service_id: str) -> Agent | None:
    """Delete an agent. Returns the agent if found, None otherwise."""
    agent = db.query(Agent).filter(Agent.id == service_id).first()
    if not agent:
        return None
    db.delete(agent)
    db.commit()
    return agent


def list_models(
    db: Session,
    *,
    provider: str | None = None,
    local: bool | None = None,
    model_status: str | None = None,
) -> list[dict]:
    """List all models across healthy agents. Returns list of model info dicts."""
    agents = db.query(Agent).filter(Agent.status == "healthy").all()

    all_models = []
    for agent in agents:
        if not agent.models:
            continue
        for model_name, model_info in agent.models.items():
            if provider and model_info.get("provider") != provider:
                continue
            if local is not None and model_info.get("local", False) != local:
                continue
            if model_status and model_info.get("status") != model_status:
                continue
            all_models.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "model_name": model_name,
                **model_info,
            })
    return all_models


def discover_agents(
    db: Session,
    capability: str,
    *,
    deployment_type: str | None = None,
    max_cost: float | None = None,
    prefer_local: bool = False,
) -> list[Agent]:
    """Find agents matching a capability with optional cost/deployment filters."""
    query = db.query(Agent).filter(Agent.status == "healthy")
    if deployment_type:
        query = query.filter(Agent.deployment_type == deployment_type)

    agents = query.all()

    matching = []
    for agent in agents:
        if not agent.capabilities:
            continue

        all_capabilities = (
            agent.capabilities.get("primary", [])
            + agent.capabilities.get("secondary", [])
        )
        if capability not in all_capabilities:
            continue

        if max_cost is not None and agent.models:
            has_affordable_model = False
            for model_info in agent.models.values():
                if prefer_local and model_info.get("local", False):
                    has_affordable_model = True
                    break
                cost = model_info.get("cost", {})
                avg_cost = (cost.get("input", 0) + cost.get("output", 0)) / 2
                if avg_cost <= max_cost:
                    has_affordable_model = True
                    break
            if not has_affordable_model:
                continue

        matching.append(agent)
    return matching
