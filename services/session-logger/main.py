import os
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import Json
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("session-logger")

app = FastAPI(title="DHG Session Logger")

# Database connection
DB_HOST = os.getenv("POSTGRES_HOST", "dhg-registry-db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "dhg")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "dhg_secure_password")
DB_NAME = os.getenv("POSTGRES_DB", "dhg_registry")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )

# Models
class SessionStart(BaseModel):
    conversation_id: str
    user_id: str = "swebber64"
    summary: Optional[str] = None
    branch: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SessionEnd(BaseModel):
    session_id: str
    summary: Optional[str] = None

class DebugLog(BaseModel):
    session_id: Optional[str] = None
    problem_statement: str
    severity: str = "Medium"
    hypotheses: List[Dict[str, Any]] = []
    fix_attempts: List[Dict[str, Any]] = []
    resolution: Optional[str] = None
    root_cause: Optional[str] = None

class KnowledgeItem(BaseModel):
    title: str
    content: str
    source_type: str = "session"
    tags: List[str] = []

@app.get("/health")
def health_check():
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/sessions/start")
def start_session(data: SessionStart):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        session_id = str(uuid.uuid4())
        
        cur.execute("""
            INSERT INTO ai_sessions 
            (session_id, conversation_id, user_id, summary, branch, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING session_id
        """, (
            session_id, 
            data.conversation_id, 
            data.user_id, 
            data.summary, 
            data.branch, 
            Json(data.metadata)
        ))
        
        conn.commit()
        conn.close()
        return {"session_id": session_id}
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logs/debug")
def log_debug(data: DebugLog):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO debug_logs 
            (session_id, problem_statement, severity, hypotheses, fix_attempts, resolution, root_cause)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING debug_id
        """, (
            data.session_id,
            data.problem_statement,
            data.severity,
            Json(data.hypotheses),
            Json(data.fix_attempts),
            data.resolution,
            data.root_cause
        ))
        
        conn.commit()
        conn.close()
        return {"status": "logged"}
    except Exception as e:
        logger.error(f"Error logging debug info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/add")
def add_knowledge(data: KnowledgeItem):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # TODO: Generate embedding here using OpenAI or local model
        # For now, inserting without embedding
        
        cur.execute("""
            INSERT INTO knowledge_items
            (title, content, source_type, tags)
            VALUES (%s, %s, %s, %s)
            RETURNING item_id
        """, (
            data.title,
            data.content,
            data.source_type,
            data.tags
        ))
        
        conn.commit()
        conn.close()
        return {"status": "added", "note": "Embedding pending"}
    except Exception as e:
        logger.error(f"Error adding knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
