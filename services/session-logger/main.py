import os
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import Json
import uuid
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("session-logger")

app = FastAPI(title="DHG Session Logger", version="1.0.0")

# Database connection
DB_HOST = os.getenv("POSTGRES_HOST", "registry-db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "dhg")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "dhg_secure_password")
DB_NAME = os.getenv("POSTGRES_DB", "dhg_registry")

# OpenAI for embeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Initialize OpenAI client (will be None if no API key)
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI client initialized for embeddings")
else:
    logger.warning("OPENAI_API_KEY not set - embeddings will be skipped")


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding vector for given text using OpenAI API.
    Returns None if OpenAI client is not configured or on error.
    """
    if not openai_client:
        logger.debug("Skipping embedding - no OpenAI client")
        return None
    
    if not text or len(text.strip()) == 0:
        logger.debug("Skipping embedding - empty text")
        return None
    
    try:
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text[:8000],  # Limit to 8000 chars to stay within token limits
            dimensions=EMBEDDING_DIMENSIONS
        )
        embedding = response.data[0].embedding
        logger.info(f"Generated embedding with {len(embedding)} dimensions")
        return embedding
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return None


# Pydantic Models
class SessionStart(BaseModel):
    conversation_id: str
    user_id: str = "swebber64"
    summary: Optional[str] = None
    branch: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionEnd(BaseModel):
    session_id: str
    summary: Optional[str] = None
    commits_made: Optional[List[str]] = None
    files_created: Optional[List[str]] = None
    files_modified: Optional[List[str]] = None


class DebugLog(BaseModel):
    session_id: Optional[str] = None
    problem_statement: str
    severity: str = "Medium"
    symptoms: Optional[List[str]] = None
    hypotheses: List[Dict[str, Any]] = []
    fix_attempts: List[Dict[str, Any]] = []
    resolution: Optional[str] = None
    root_cause: Optional[str] = None
    prevention: Optional[str] = None
    duration_minutes: Optional[int] = None


class KnowledgeItem(BaseModel):
    title: str
    content: str
    source_type: str = "session"
    source_id: Optional[str] = None
    tags: List[str] = []


class SessionFile(BaseModel):
    session_id: str
    file_path: str
    file_type: Optional[str] = None
    content: str


# Health Check
@app.get("/health")
def health_check():
    """Check service health and database connectivity."""
    db_status = "unknown"
    embedding_status = "disabled" if not openai_client else "enabled"
    
    try:
        conn = get_db_connection()
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Health check DB error: {e}")
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "embeddings": embedding_status
    }


# Session Endpoints
@app.post("/sessions/start")
def start_session(data: SessionStart):
    """Start a new AI session and return session_id."""
    logger.info(f"Starting session for conversation: {data.conversation_id}")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        session_id = str(uuid.uuid4())
        
        # Generate embedding for summary if provided
        embedding = None
        if data.summary:
            embedding = generate_embedding(data.summary)
        
        cur.execute("""
            INSERT INTO ai_sessions 
            (session_id, conversation_id, user_id, summary, branch, metadata, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING session_id
        """, (
            session_id, 
            data.conversation_id, 
            data.user_id, 
            data.summary, 
            data.branch, 
            Json(data.metadata),
            embedding
        ))
        
        conn.commit()
        logger.info(f"Session started: {session_id}")
        return {"session_id": session_id, "status": "created"}
        
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")
    finally:
        if conn:
            conn.close()


@app.post("/sessions/end")
def end_session(data: SessionEnd):
    """End an AI session with final summary and file lists."""
    logger.info(f"Ending session: {data.session_id}")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Generate embedding for final summary if provided
        embedding = None
        if data.summary:
            embedding = generate_embedding(data.summary)
        
        cur.execute("""
            UPDATE ai_sessions 
            SET ended_at = CURRENT_TIMESTAMP,
                summary = COALESCE(%s, summary),
                embedding = COALESCE(%s, embedding),
                commits_made = %s,
                files_created = %s,
                files_modified = %s
            WHERE session_id = %s
            RETURNING session_id
        """, (
            data.summary,
            embedding,
            data.commits_made,
            data.files_created,
            data.files_modified,
            data.session_id
        ))
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Session not found: {data.session_id}")
        
        conn.commit()
        logger.info(f"Session ended: {data.session_id}")
        return {"session_id": data.session_id, "status": "ended"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")
    finally:
        if conn:
            conn.close()


# Debug Log Endpoints
@app.post("/logs/debug")
def log_debug(data: DebugLog):
    """Log a debug session with hypotheses, fixes, and resolution."""
    logger.info(f"Logging debug for session: {data.session_id}")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO debug_logs 
            (session_id, problem_statement, severity, symptoms, hypotheses, 
             fix_attempts, resolution, root_cause, prevention, duration_minutes,
             resolved_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING debug_id
        """, (
            data.session_id,
            data.problem_statement,
            data.severity,
            data.symptoms,
            Json(data.hypotheses),
            Json(data.fix_attempts),
            data.resolution,
            data.root_cause,
            data.prevention,
            data.duration_minutes,
            'CURRENT_TIMESTAMP' if data.resolution else None
        ))
        
        debug_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"Debug logged: {debug_id}")
        return {"debug_id": str(debug_id), "status": "logged"}
        
    except Exception as e:
        logger.error(f"Error logging debug info: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log debug: {str(e)}")
    finally:
        if conn:
            conn.close()


# Knowledge Endpoints
@app.post("/knowledge/add")
def add_knowledge(data: KnowledgeItem):
    """Add a knowledge item with embedding for RAG retrieval."""
    logger.info(f"Adding knowledge item: {data.title}")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Generate embedding for content
        text_for_embedding = f"{data.title}\n\n{data.content}"
        embedding = generate_embedding(text_for_embedding)
        
        cur.execute("""
            INSERT INTO knowledge_items
            (title, content, source_type, source_id, tags, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING item_id
        """, (
            data.title,
            data.content,
            data.source_type,
            data.source_id,
            data.tags,
            embedding
        ))
        
        item_id = cur.fetchone()[0]
        conn.commit()
        
        embedded_status = "with embedding" if embedding else "without embedding"
        logger.info(f"Knowledge added: {item_id} ({embedded_status})")
        return {
            "item_id": str(item_id), 
            "status": "added",
            "embedded": embedding is not None
        }
        
    except Exception as e:
        logger.error(f"Error adding knowledge: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add knowledge: {str(e)}")
    finally:
        if conn:
            conn.close()


# Session Files Endpoints
@app.post("/files/add")
def add_session_file(data: SessionFile):
    """Add a file artifact from a session with embedding."""
    logger.info(f"Adding file: {data.file_path} for session: {data.session_id}")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Generate content hash
        import hashlib
        content_hash = hashlib.sha256(data.content.encode()).hexdigest()
        
        # Generate embedding for file content
        embedding = generate_embedding(data.content)
        
        cur.execute("""
            INSERT INTO session_files
            (session_id, file_path, file_type, content_hash, content, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING file_id
        """, (
            data.session_id,
            data.file_path,
            data.file_type,
            content_hash,
            data.content,
            embedding
        ))
        
        file_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"File added: {file_id}")
        return {
            "file_id": str(file_id),
            "content_hash": content_hash,
            "status": "added",
            "embedded": embedding is not None
        }
        
    except Exception as e:
        logger.error(f"Error adding file: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add file: {str(e)}")
    finally:
        if conn:
            conn.close()


# Search Endpoint (uses embeddings)
@app.post("/search")
def search_knowledge(query: str, limit: int = 10):
    """Semantic search across knowledge items using embeddings."""
    logger.info(f"Searching knowledge for: {query[:50]}...")
    
    if not openai_client:
        raise HTTPException(
            status_code=503, 
            detail="Search unavailable - embeddings not configured"
        )
    
    conn = None
    try:
        # Generate query embedding
        query_embedding = generate_embedding(query)
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Vector similarity search using pgvector
        cur.execute("""
            SELECT item_id, title, content, tags,
                   1 - (embedding <=> %s::vector) as similarity
            FROM knowledge_items
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, limit))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "item_id": str(row[0]),
                "title": row[1],
                "content": row[2][:500],  # Truncate content for response
                "tags": row[3],
                "similarity": float(row[4])
            })
        
        logger.info(f"Found {len(results)} results")
        return {"query": query, "results": results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting DHG Session Logger service")
    uvicorn.run(app, host="0.0.0.0", port=8009)
