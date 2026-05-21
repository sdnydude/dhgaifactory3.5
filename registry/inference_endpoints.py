"""DHG Inference Platform API - Node discovery, model routing, interaction logging."""
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
import inference_service as svc
from inference_schemas import (
    NodeRegisterRequest, NodeResponse, NodeHeartbeatRequest, NodeDrainRequest,
    ModelEndpoint, InteractionLogRequest, InteractionLogResponse, RoutingConfigResponse,
)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
)

logger = logging.getLogger("dhg.inference.endpoints")
inference_router = APIRouter(prefix="/api/v1/inference", tags=["inference"])


@inference_router.get("/nodes", response_model=list[NodeResponse])
def list_nodes(db: Session = Depends(get_db)):
    start = time.time()
    result = svc.list_nodes(db)
    registry_read_operations.labels(operation="list_nodes").inc()
    registry_read_latency.observe((time.time() - start) * 1000)
    return result


@inference_router.post("/nodes/register", response_model=NodeResponse)
def register_node(req: NodeRegisterRequest, db: Session = Depends(get_db)):
    start = time.time()
    node = svc.register_or_update_node(db, req)
    logger.info(f"Node registered: {node.node_name} ({node.host}:{node.gateway_port})")
    registry_write_operations.labels(operation="register_node").inc()
    registry_write_latency.observe((time.time() - start) * 1000)
    return node


@inference_router.post("/nodes/heartbeat")
def node_heartbeat(req: NodeHeartbeatRequest, db: Session = Depends(get_db)):
    node = svc.heartbeat(db, req.node_name)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {req.node_name} not found")
    return {"status": "ok"}


@inference_router.post("/nodes/drain")
def drain_node(req: NodeDrainRequest, db: Session = Depends(get_db)):
    node = svc.set_node_status(db, req.node_name, "draining")
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {req.node_name} not found")
    return {"status": "draining"}


@inference_router.post("/nodes/activate")
def activate_node(req: NodeDrainRequest, db: Session = Depends(get_db)):
    node = svc.set_node_status(db, req.node_name, "online")
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {req.node_name} not found")
    return {"status": "online"}


@inference_router.get("/models", response_model=list[ModelEndpoint])
def list_models(
    task_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    results = svc.list_models(db, task_type=task_type)
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
    start = time.time()
    interaction = svc.log_interaction(db, req)
    registry_write_operations.labels(operation="log_interaction").inc()
    registry_write_latency.observe((time.time() - start) * 1000)
    return InteractionLogResponse(id=interaction.id, synced_at=interaction.synced_at)


@inference_router.get("/interactions")
def query_interactions(
    task_type: Optional[str] = None,
    model_source: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    return svc.query_interactions(db, task_type=task_type, model_source=model_source, limit=limit)


@inference_router.get("/routing", response_model=list[RoutingConfigResponse])
def list_routing_config(db: Session = Depends(get_db)):
    return svc.list_routing_config(db)
