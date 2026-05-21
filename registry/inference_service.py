"""Inference platform service — DB operations for nodes, models, interactions, routing."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, and_

from models import InferenceNode, InferenceModel, LLMInteraction, RoutingConfig

logger = logging.getLogger(__name__)


def list_nodes(db: Session) -> list[InferenceNode]:
    return db.query(InferenceNode).all()


def register_or_update_node(db: Session, req) -> InferenceNode:
    """Register a new node or update existing. Also syncs model list."""
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()
    if node:
        node.host = req.host
        node.gateway_port = req.gateway_port
        node.ollama_port = req.ollama_port
        node.gpu_model = req.gpu_model
        node.gpu_vram_gb = req.gpu_vram_gb
        node.ram_gb = req.ram_gb
        node.fallback_enabled = req.fallback_enabled
        node.status = "online"
        node.last_heartbeat = sa_func.now()
    else:
        node = InferenceNode(
            node_name=req.node_name, host=req.host,
            gateway_port=req.gateway_port, ollama_port=req.ollama_port,
            gpu_model=req.gpu_model, gpu_vram_gb=req.gpu_vram_gb,
            ram_gb=req.ram_gb, fallback_enabled=req.fallback_enabled,
            status="online", last_heartbeat=sa_func.now(),
        )
        db.add(node)
    db.flush()

    for m in req.models:
        existing = db.query(InferenceModel).filter(
            and_(InferenceModel.node_id == node.id, InferenceModel.model_name == m.model_name)
        ).first()
        if existing:
            existing.model_alias = m.model_alias
            existing.task_types = m.task_types
            existing.priority = m.priority
            existing.vram_usage_gb = m.vram_usage_gb
            existing.max_context_length = m.max_context_length
            existing.loaded = True
        else:
            db.add(InferenceModel(
                node_id=node.id, model_name=m.model_name,
                model_alias=m.model_alias, task_types=m.task_types,
                priority=m.priority, vram_usage_gb=m.vram_usage_gb,
                max_context_length=m.max_context_length, loaded=True,
            ))
    db.commit()
    db.refresh(node)
    return node


def heartbeat(db: Session, node_name: str) -> InferenceNode | None:
    node = db.query(InferenceNode).filter(InferenceNode.node_name == node_name).first()
    if not node:
        return None
    node.last_heartbeat = sa_func.now()
    if node.status == "offline":
        node.status = "online"
    db.commit()
    return node


def set_node_status(db: Session, node_name: str, status: str) -> InferenceNode | None:
    """Set node status (draining, online, etc). Returns None if not found."""
    node = db.query(InferenceNode).filter(InferenceNode.node_name == node_name).first()
    if not node:
        return None
    node.status = status
    if status == "online":
        node.last_heartbeat = sa_func.now()
    db.commit()
    return node


def list_models(
    db: Session, *, task_type: str | None = None,
) -> list[tuple]:
    """Return list of (InferenceModel, InferenceNode) tuples for online nodes."""
    query = (
        db.query(InferenceModel, InferenceNode)
        .join(InferenceNode, InferenceModel.node_id == InferenceNode.id)
        .filter(InferenceNode.status == "online")
    )
    if task_type:
        route = db.query(RoutingConfig).filter(
            RoutingConfig.task_type == task_type, RoutingConfig.enabled == True,
        ).first()
        if route and route.prefer.startswith("local:"):
            alias = route.prefer.split(":", 1)[1]
            query = query.filter(InferenceModel.model_alias == alias)
        elif route and route.prefer == "claude":
            return []
        else:
            query = query.filter(InferenceModel.task_types.any(task_type))

    return query.order_by(InferenceModel.priority.asc()).all()


def log_interaction(db: Session, req) -> LLMInteraction:
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()
    interaction = LLMInteraction(
        timestamp=req.timestamp, user_id=req.user_id,
        node_id=node.id if node else None,
        model_name=req.model_name, model_source=req.model_source,
        model_digest=req.model_digest, task_type=req.task_type,
        agent_name=req.agent_name, session_id=req.session_id,
        prompt_tokens=req.prompt_tokens, completion_tokens=req.completion_tokens,
        latency_ms=req.latency_ms, input_hash=req.input_hash,
        input_summary=req.input_summary, input_has_image=req.input_has_image,
        output=req.output, output_validated=req.output_validated,
        output_schema_name=req.output_schema_name,
        fallback_used=req.fallback_used, fallback_reason=req.fallback_reason,
        retry_count=req.retry_count, estimated_cost_usd=req.estimated_cost_usd,
        synced_at=sa_func.now(),
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


def query_interactions(
    db: Session,
    *,
    task_type: str | None = None,
    model_source: str | None = None,
    limit: int = 50,
) -> list[LLMInteraction]:
    query = db.query(LLMInteraction).order_by(LLMInteraction.timestamp.desc())
    if task_type:
        query = query.filter(LLMInteraction.task_type == task_type)
    if model_source:
        query = query.filter(LLMInteraction.model_source == model_source)
    return query.limit(limit).all()


def list_routing_config(db: Session) -> list[RoutingConfig]:
    return db.query(RoutingConfig).filter(RoutingConfig.enabled == True).all()
