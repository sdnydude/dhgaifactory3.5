from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Generic, TypeVar
from enum import Enum
from datetime import datetime
import uuid

class MessageType(str, Enum):
    TASK_REQUEST = "task.request"
    TASK_RESPONSE = "task.response"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    # Content types
    CONTENT_CHUNK = "content.chunk"
    CONTENT_COMPLETE = "content.complete"

class BaseMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: MessageType
    source: str
    target: str = "*"
    trace_id: Optional[str] = None

T = TypeVar('T')

class AgentResponse(BaseMessage, Generic[T]):
    type: MessageType = MessageType.TASK_RESPONSE
    payload: T
    warnings: List[str] = []
    metadata: Dict[str, Any] = {}

class AgentError(BaseMessage):
    type: MessageType = MessageType.ERROR
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
