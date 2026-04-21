"""Pydantic schemas for inference platform API."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ModelRegisterRequest(BaseModel):
    model_name: str
    model_alias: Optional[str] = None
    task_types: list[str] = []
    priority: int = 1
    vram_usage_gb: Optional[float] = None
    max_context_length: Optional[int] = None


class NodeRegisterRequest(BaseModel):
    node_name: str
    host: str
    gateway_port: int = 8100
    ollama_port: int = 11434
    gpu_model: Optional[str] = None
    gpu_vram_gb: Optional[int] = None
    ram_gb: Optional[int] = None
    fallback_enabled: bool = True
    models: list[ModelRegisterRequest] = []


class NodeResponse(BaseModel):
    id: UUID
    node_name: str
    host: str
    gateway_port: int
    ollama_port: int
    gpu_model: Optional[str]
    gpu_vram_gb: Optional[int]
    ram_gb: Optional[int]
    status: str
    fallback_enabled: bool
    last_heartbeat: Optional[datetime]
    registered_at: datetime

    class Config:
        from_attributes = True


class NodeHeartbeatRequest(BaseModel):
    node_name: str
    gpu_memory_used_bytes: Optional[int] = None
    gpu_memory_total_bytes: Optional[int] = None
    loaded_models: list[str] = []
    queue_depth: int = 0


class NodeDrainRequest(BaseModel):
    node_name: str


class ModelEndpoint(BaseModel):
    node_name: str
    host: str
    port: int
    model_name: str
    model_alias: Optional[str]
    task_types: list[str]
    priority: int


class InteractionLogRequest(BaseModel):
    timestamp: datetime
    user_id: Optional[UUID] = None
    node_name: str
    model_name: str
    model_source: str
    model_digest: Optional[str] = None
    task_type: Optional[str] = None
    agent_name: Optional[str] = None
    session_id: Optional[UUID] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    input_hash: Optional[str] = None
    input_summary: Optional[str] = None
    input_has_image: bool = False
    output: Optional[dict] = None
    output_validated: Optional[bool] = None
    output_schema_name: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    retry_count: int = 0
    estimated_cost_usd: Optional[float] = None


class InteractionLogResponse(BaseModel):
    id: UUID
    synced_at: datetime

    class Config:
        from_attributes = True


class RoutingConfigResponse(BaseModel):
    task_type: str
    prefer: str
    fallback: Optional[str]
    enabled: bool

    class Config:
        from_attributes = True
