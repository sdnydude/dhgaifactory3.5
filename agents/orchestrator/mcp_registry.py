"""
DHG AI Factory - MCP Registry Storage
Server-Sent Events (SSE) endpoint for storing conversations and artifacts
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json
import structlog
import os

# Database imports
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

logger = structlog.get_logger()

# Router for MCP endpoints
mcp_router = APIRouter(tags=["MCP Registry"])


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

REGISTRY_DB_URL = os.getenv(
    "REGISTRY_DB_URL", 
    "postgresql://dhg:weenie64@10.0.0.251:5432/dhg_registry"
)

try:
    engine = create_engine(REGISTRY_DB_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    DB_CONNECTED = True
except Exception as e:
    logger.error("registry_db_connection_failed", error=str(e))
    engine = None
    SessionLocal = None
    DB_CONNECTED = False


@contextmanager
def get_db():
    """Database session context manager"""
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not available")
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# MCP TOOL SCHEMAS
# ============================================================================

class SaveConversationParams(BaseModel):
    title: str
    messages: List[Dict[str, Any]]
    model_name: Optional[str] = None
    project_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SaveArtifactParams(BaseModel):
    title: str
    artifact_type: str  # code, document, image, data
    content: str
    language: Optional[str] = None
    conversation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchParams(BaseModel):
    query: str
    limit: int = 20


class GetArtifactParams(BaseModel):
    artifact_id: str


class LogEventParams(BaseModel):
    event_type: str
    entity_type: str
    entity_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPToolCall(BaseModel):
    tool: str
    params: Dict[str, Any]


# ============================================================================
# MCP TOOLS
# ============================================================================

MCP_TOOLS = [
    {
        "name": "save_conversation",
        "description": "Save a conversation with its messages to the central registry",
        "inputSchema": SaveConversationParams.model_json_schema()
    },
    {
        "name": "save_artifact",
        "description": "Save a generated artifact (code, document, image) to the registry",
        "inputSchema": SaveArtifactParams.model_json_schema()
    },
    {
        "name": "search_conversations",
        "description": "Search past conversations by keyword",
        "inputSchema": SearchParams.model_json_schema()
    },
    {
        "name": "get_artifact",
        "description": "Retrieve a stored artifact by its ID",
        "inputSchema": GetArtifactParams.model_json_schema()
    },
    {
        "name": "log_event",
        "description": "Log an event to the audit trail",
        "inputSchema": LogEventParams.model_json_schema()
    },
    {
        "name": "list_recent",
        "description": "List recent conversations and artifacts",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}}
    }
]


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def save_conversation(params: Dict[str, Any]) -> Dict[str, Any]:
    """Save a conversation to the registry"""
    try:
        with get_db() as db:
            conv_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Insert conversation
            db.execute(text("""
                INSERT INTO conversations (id, title, conversation_id, export_source, model_name, created_at, updated_at, meta_data)
                VALUES (:id, :title, :conv_id, :source, :model, :created, :updated, :meta)
            """), {
                "id": conv_id,
                "title": params.get("title", "Untitled"),
                "conv_id": conv_id,
                "source": "mcp",
                "model": params.get("model_name"),
                "created": now,
                "updated": now,
                "meta": json.dumps(params.get("metadata", {}))
            })
            
            # Insert messages
            for idx, msg in enumerate(params.get("messages", [])):
                msg_id = str(uuid.uuid4())
                db.execute(text("""
                    INSERT INTO messages (id, conversation_id, message_index, role, content, created_at, meta_data)
                    VALUES (:id, :conv_id, :idx, :role, :content, :created, :meta)
                """), {
                    "id": msg_id,
                    "conv_id": conv_id,
                    "idx": idx,
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "created": now,
                    "meta": json.dumps(msg.get("metadata", {}))
                })
            
            logger.info("conversation_saved", conversation_id=conv_id, message_count=len(params.get("messages", [])))
            return {"success": True, "conversation_id": conv_id}
    except Exception as e:
        logger.error("save_conversation_failed", error=str(e))
        return {"success": False, "error": str(e)}


def save_artifact(params: Dict[str, Any]) -> Dict[str, Any]:
    """Save an artifact to the registry"""
    try:
        with get_db() as db:
            artifact_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Need a conversation_id - create one if not provided
            conv_id = params.get("conversation_id")
            if not conv_id:
                conv_id = str(uuid.uuid4())
                db.execute(text("""
                    INSERT INTO conversations (id, title, conversation_id, export_source, created_at, updated_at)
                    VALUES (:id, :title, :conv_id, :source, :created, :updated)
                """), {
                    "id": conv_id,
                    "title": f'Artifact: {params.get("title", "Untitled")}',
                    "conv_id": conv_id,
                    "source": "mcp_artifact",
                    "created": now,
                    "updated": now
                })
            
            db.execute(text("""
                INSERT INTO artifacts (id, conversation_id, title, artifact_type, language, content, created_at, meta_data)
                VALUES (:id, :conv_id, :title, :type, :lang, :content, :created, :meta)
            """), {
                "id": artifact_id,
                "conv_id": conv_id,
                "title": params.get("title", "Untitled"),
                "type": params.get("artifact_type", "code"),
                "lang": params.get("language"),
                "content": params.get("content", ""),
                "created": now,
                "meta": json.dumps(params.get("metadata", {}))
            })
            
            logger.info("artifact_saved", artifact_id=artifact_id)
            return {"success": True, "artifact_id": artifact_id, "conversation_id": conv_id}
    except Exception as e:
        logger.error("save_artifact_failed", error=str(e))
        return {"success": False, "error": str(e)}


def search_conversations(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search conversations by keyword"""
    try:
        with get_db() as db:
            query = params.get("query", "")
            limit = params.get("limit", 20)
            
            result = db.execute(text("""
                SELECT c.id, c.title, c.model_name, c.created_at,
                       (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) as message_count
                FROM conversations c
                WHERE c.title ILIKE :query
                ORDER BY c.created_at DESC
                LIMIT :limit
            """), {"query": f"%{query}%", "limit": limit})
            
            conversations = []
            for row in result:
                conversations.append({
                    "id": str(row[0]),
                    "title": row[1],
                    "model_name": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "message_count": row[4]
                })
            
            return {"success": True, "conversations": conversations, "count": len(conversations)}
    except Exception as e:
        logger.error("search_conversations_failed", error=str(e))
        return {"success": False, "error": str(e)}


def get_artifact(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get an artifact by ID"""
    try:
        with get_db() as db:
            artifact_id = params.get("artifact_id")
            
            result = db.execute(text("""
                SELECT id, title, artifact_type, language, content, created_at, meta_data
                FROM artifacts
                WHERE id = :id
            """), {"id": artifact_id})
            
            row = result.fetchone()
            if not row:
                return {"success": False, "error": "Artifact not found"}
            
            return {
                "success": True,
                "artifact": {
                    "id": str(row[0]),
                    "title": row[1],
                    "artifact_type": row[2],
                    "language": row[3],
                    "content": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "metadata": row[6]
                }
            }
    except Exception as e:
        logger.error("get_artifact_failed", error=str(e))
        return {"success": False, "error": str(e)}


def log_event(params: Dict[str, Any]) -> Dict[str, Any]:
    """Log an event for audit trail"""
    try:
        with get_db() as db:
            event_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            db.execute(text("""
                INSERT INTO events (id, event_type, entity_type, entity_id, description, meta_data, created_at)
                VALUES (:id, :event_type, :entity_type, :entity_id, :description, :meta, :created)
            """), {
                "id": event_id,
                "event_type": params.get("event_type", "unknown"),
                "entity_type": params.get("entity_type", "unknown"),
                "entity_id": params.get("entity_id"),
                "description": params.get("description"),
                "meta": json.dumps(params.get("metadata", {})),
                "created": now
            })
            
            logger.info("event_logged", event_id=event_id, event_type=params.get("event_type"))
            return {"success": True, "event_id": event_id}
    except Exception as e:
        logger.error("log_event_failed", error=str(e))
        return {"success": False, "error": str(e)}


def list_recent(params: Dict[str, Any]) -> Dict[str, Any]:
    """List recent conversations and artifacts"""
    try:
        with get_db() as db:
            limit = params.get("limit", 10)
            
            # Recent conversations
            conv_result = db.execute(text("""
                SELECT id, title, model_name, created_at
                FROM conversations
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit})
            
            conversations = [{"id": str(r[0]), "title": r[1], "model": r[2], "created": r[3].isoformat() if r[3] else None}
                           for r in conv_result]
            
            # Recent artifacts
            art_result = db.execute(text("""
                SELECT id, title, artifact_type, created_at
                FROM artifacts
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit})
            
            artifacts = [{"id": str(r[0]), "title": r[1], "type": r[2], "created": r[3].isoformat() if r[3] else None}
                        for r in art_result]
            
            return {"success": True, "conversations": conversations, "artifacts": artifacts}
    except Exception as e:
        logger.error("list_recent_failed", error=str(e))
        return {"success": False, "error": str(e)}


# Tool dispatcher
TOOL_HANDLERS = {
    "save_conversation": save_conversation,
    "save_artifact": save_artifact,
    "search_conversations": search_conversations,
    "get_artifact": get_artifact,
    "log_event": log_event,
    "list_recent": list_recent
}


# ============================================================================
# MCP ENDPOINTS
# ============================================================================

@mcp_router.get("/tools")
async def list_tools():
    """List available MCP tools"""
    return {"tools": MCP_TOOLS}


@mcp_router.post("/call")
async def call_tool(request: MCPToolCall):
    """Execute an MCP tool"""
    tool_name = request.tool
    
    if tool_name not in TOOL_HANDLERS:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
    
    handler = TOOL_HANDLERS[tool_name]
    result = handler(request.params)
    
    return {"tool": tool_name, "result": result}


@mcp_router.get("/health")
async def mcp_health():
    """MCP Registry health check"""
    return {
        "status": "healthy" if DB_CONNECTED else "degraded",
        "database_connected": DB_CONNECTED,
        "tools_available": len(MCP_TOOLS)
    }
