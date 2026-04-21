"""
DHG Inference Platform API - Node discovery, model routing, interaction logging.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, and_

from database import get_db
from models import InferenceNode, InferenceModel, LLMInteraction, RoutingConfig
from inference_schemas import (
    NodeRegisterRequest, NodeResponse, NodeHeartbeatRequest, NodeDrainRequest,
    ModelEndpoint, InteractionLogRequest, InteractionLogResponse, RoutingConfigResponse,
)

logger = logging.getLogger("dhg.inference.endpoints")
inference_router = APIRouter(prefix="/api/v1/inference", tags=["inference"])


@inference_router.get("/nodes", response_model=list[NodeResponse])
def list_nodes(db: Session = Depends(get_db)):
    return db.query(InferenceNode).all()


@inference_router.post("/nodes/register", response_model=NodeResponse)
def register_node(req: NodeRegisterRequest, db: Session = Depends(get_db)):
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
    logger.info(f"Node registered: {node.node_name} ({node.host}:{node.gateway_port})")
    return node


@inference_router.post("/nodes/heartbeat")
def node_heartbeat(req: NodeHeartbeatRequest, db: Session = Depends(get_db)):
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {req.node_name} not found")
    node.last_heartbeat = sa_func.now()
    if node.status == "offline":
        node.status = "online"
    db.commit()
    return {"status": "ok"}


@inference_router.post("/nodes/drain")
def drain_node(req: NodeDrainRequest, db: Session = Depends(get_db)):
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {req.node_name} not found")
    node.status = "draining"
    db.commit()
    return {"status": "draining"}


@inference_router.post("/nodes/activate")
def activate_node(req: NodeDrainRequest, db: Session = Depends(get_db)):
    node = db.query(InferenceNode).filter(InferenceNode.node_name == req.node_name).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {req.node_name} not found")
    node.status = "online"
    node.last_heartbeat = sa_func.now()
    db.commit()
    return {"status": "online"}


@inference_router.get("/models", response_model=list[ModelEndpoint])
def list_models(
    task_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
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

    results = query.order_by(InferenceModel.priority.asc()).all()
    return [
        ModelEndpoint(
            node_name=node.node_name, host=node.host, port=node.gateway_port,
            model_name=model.model_name, model_alias=model.model_alias,
            task_types=model.task_types or [], priority=model.priority,
        )
        for model, node in results
    ]


@inference_router.post("/interactions", response_model=InteractionLogResponse)
def log_interaction(req: InteractionLogRequest, db: Session = Depends(get_db)):
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
    return InteractionLogResponse(id=interaction.id, synced_at=interaction.synced_at)


@inference_router.get("/interactions")
def query_interactions(
    task_type: Optional[str] = None,
    model_source: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(LLMInteraction).order_by(LLMInteraction.timestamp.desc())
    if task_type:
        query = query.filter(LLMInteraction.task_type == task_type)
    if model_source:
        query = query.filter(LLMInteraction.model_source == model_source)
    return query.limit(limit).all()


@inference_router.get("/routing", response_model=list[RoutingConfigResponse])
def list_routing_config(db: Session = Depends(get_db)):
    return db.query(RoutingConfig).filter(RoutingConfig.enabled == True).all()
