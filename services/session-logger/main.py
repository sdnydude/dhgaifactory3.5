import os
import re
import logging
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
import psycopg2
import psycopg2.pool
from psycopg2.extras import Json
import uuid
import httpx
from prometheus_client import Counter, Histogram, generate_latest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("session-logger")

# Database connection
DB_HOST = os.getenv("POSTGRES_HOST", "registry-db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "dhg")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "dhg_secure_password")
DB_NAME = os.getenv("POSTGRES_DB", "dhg_registry")
DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "2"))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))

# Ollama for embeddings and summarization
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
EMBED_MODEL = "nomic-embed-text"
EMBED_DIMENSIONS = 768
SUMMARIZE_MODEL = os.getenv("SUMMARIZE_MODEL", "qwen3:14b")

# Chunk size for splitting logs
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "2000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Connection pool (initialized at module level, cleaned up via lifespan)
db_pool = psycopg2.pool.ThreadedConnectionPool(
    DB_POOL_MIN, DB_POOL_MAX,
    host=DB_HOST, port=DB_PORT, user=DB_USER,
    password=DB_PASS, dbname=DB_NAME,
)
logger.info(f"Database connection pool initialized (min={DB_POOL_MIN}, max={DB_POOL_MAX})")

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------
session_logger_read_latency = Histogram(
    'session_logger_read_latency',
    'Database read latency in milliseconds',
    ['operation'],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

session_logger_read_operations = Counter(
    'session_logger_read_operations',
    'Total number of read operations',
    ['operation'],
)

session_logger_errors = Counter(
    'session_logger_errors',
    'Total number of errors',
    ['error_type'],
)


@asynccontextmanager
async def lifespan(app):
    yield
    if db_pool and not db_pool.closed:
        db_pool.closeall()
        logger.info("Database connection pool closed")


app = FastAPI(title="DHG Session Logger", version="2.0.0", lifespan=lifespan)


def get_db_connection():
    try:
        return db_pool.getconn()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


def return_db_connection(conn):
    try:
        db_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Failed to return connection to pool: {e}")


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def ollama_embed(text: str) -> Optional[List[float]]:
    """Generate 768-dim embedding via Ollama nomic-embed-text."""
    if not text or not text.strip():
        return None
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": text[:8000]},
            timeout=30.0,
        )
        resp.raise_for_status()
        embeddings = resp.json().get("embeddings")
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        return None
    except Exception as e:
        logger.error(f"Ollama embedding failed: {e}")
        return None


def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate 768-dim embedding via Ollama. Used by all endpoints."""
    return ollama_embed(text)


# ---------------------------------------------------------------------------
# Text processing helpers
# ---------------------------------------------------------------------------

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub('', text)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# Ollama summarization
# ---------------------------------------------------------------------------

def ollama_summarize(text: str) -> Optional[str]:
    """Summarize terminal session text via Ollama."""
    prompt = (
        "Summarize this terminal session log. Extract: "
        "1) What commands were run, 2) What errors occurred, "
        "3) What was accomplished, 4) Key files touched. "
        "Be concise.\n\n" + text[:12000]
    )
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": SUMMARIZE_MODEL, "prompt": prompt, "stream": False},
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        logger.error(f"Ollama summarization failed: {e}")
        return None


def extract_entities(text: str) -> List[Dict[str, str]]:
    """Extract commands, file paths, and error patterns from session text."""
    entities = []
    # Commands (lines starting with $ or common prompts)
    for match in re.finditer(r'(?:^|\n)\s*[\$#>]\s+(\S+)', text):
        cmd = match.group(1)
        if cmd and len(cmd) > 1 and not cmd.startswith('-'):
            entities.append({"name": cmd, "node_type": "command"})
    # File paths
    for match in re.finditer(r'(?:/[\w.\-]+){2,}', text):
        entities.append({"name": match.group(0), "node_type": "file_path"})
    # Error patterns
    for match in re.finditer(r'(?:error|Error|ERROR|FATAL|fatal|exception|Exception)[:\s]+(.{10,80})', text):
        entities.append({"name": match.group(0).strip()[:120], "node_type": "error"})
    # Deduplicate by name
    seen = set()
    unique = []
    for e in entities:
        if e["name"] not in seen:
            seen.add(e["name"])
            unique.append(e)
    return unique


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

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


class TerminalLogIngest(BaseModel):
    hostname: str
    username: str = "swebber64"
    raw_log: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None


class ConceptLink(BaseModel):
    source_name: str
    target_name: str
    relationship: str = "related_to"
    source_type: str = "concept"
    target_type: str = "concept"
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Stats Response Models
# ---------------------------------------------------------------------------

class StatsOverview(BaseModel):
    total_sessions: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    total_concepts: int = Field(ge=0)
    total_edges: int = Field(ge=0)
    avg_chunks_per_session: float = Field(ge=0.0)
    embedding_coverage_pct: float = Field(ge=0.0, le=100.0)
    earliest_session: Optional[str] = None
    latest_session: Optional[str] = None


class DailySessionCount(BaseModel):
    date: str
    session_count: int = Field(ge=0)


class DailyStats(BaseModel):
    days: List[DailySessionCount]
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class ConceptRanking(BaseModel):
    name: str = Field(min_length=1)
    node_type: str
    edge_count: int = Field(gt=0)


class NodeTypeBreakdown(BaseModel):
    node_type: str
    count: int = Field(gt=0)


class ConceptStats(BaseModel):
    top_concepts: List[ConceptRanking]
    node_type_breakdown: List[NodeTypeBreakdown]
    total_nodes: int = Field(ge=0)
    total_edges: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


@app.get("/health")
def health_check():
    db_status = "unknown"
    ollama_status = "unknown"
    try:
        conn = get_db_connection()
        return_db_connection(conn)
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        ollama_status = "connected" if resp.status_code == 200 else f"error: {resp.status_code}"
    except Exception as e:
        ollama_status = f"error: {str(e)}"

    healthy = db_status == "connected"
    return {
        "status": "healthy" if healthy else "degraded",
        "database": db_status,
        "ollama": ollama_status,
        "embeddings": "ollama/nomic-embed-text (768d)",
        "summarization": f"ollama/{SUMMARIZE_MODEL}",
    }


# ---------------------------------------------------------------------------
# Existing Session Endpoints (preserved)
# ---------------------------------------------------------------------------

@app.post("/sessions/start")
def start_session(data: SessionStart):
    logger.info(f"Starting session for conversation: {data.conversation_id}")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        session_id = str(uuid.uuid4())
        embedding = generate_embedding(data.summary) if data.summary else None
        cur.execute("""
            INSERT INTO ai_sessions
            (session_id, conversation_id, user_id, summary, branch, metadata, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING session_id
        """, (session_id, data.conversation_id, data.user_id, data.summary,
              data.branch, Json(data.metadata), embedding))
        conn.commit()
        return {"session_id": session_id, "status": "created"}
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/sessions/end")
def end_session(data: SessionEnd):
    logger.info(f"Ending session: {data.session_id}")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        embedding = generate_embedding(data.summary) if data.summary else None
        cur.execute("""
            UPDATE ai_sessions
            SET ended_at = CURRENT_TIMESTAMP,
                summary = COALESCE(%s, summary),
                embedding = COALESCE(%s, embedding),
                commits_made = %s, files_created = %s, files_modified = %s
            WHERE session_id = %s RETURNING session_id
        """, (data.summary, embedding, data.commits_made,
              data.files_created, data.files_modified, data.session_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Session not found: {data.session_id}")
        conn.commit()
        return {"session_id": data.session_id, "status": "ended"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/logs/debug")
def log_debug(data: DebugLog):
    logger.info(f"Logging debug for session: {data.session_id}")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO debug_logs
            (session_id, problem_statement, severity, symptoms, hypotheses,
             fix_attempts, resolution, root_cause, prevention, duration_minutes, resolved_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING debug_id
        """, (data.session_id, data.problem_statement, data.severity,
              data.symptoms, Json(data.hypotheses), Json(data.fix_attempts),
              data.resolution, data.root_cause, data.prevention,
              data.duration_minutes,
              'CURRENT_TIMESTAMP' if data.resolution else None))
        debug_id = cur.fetchone()[0]
        conn.commit()
        return {"debug_id": str(debug_id), "status": "logged"}
    except Exception as e:
        logger.error(f"Error logging debug info: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/knowledge/add")
def add_knowledge(data: KnowledgeItem):
    logger.info(f"Adding knowledge item: {data.title}")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        text_for_embedding = f"{data.title}\n\n{data.content}"
        embedding = generate_embedding(text_for_embedding)
        cur.execute("""
            INSERT INTO knowledge_items (title, content, source_type, source_id, tags, embedding)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING item_id
        """, (data.title, data.content, data.source_type, data.source_id,
              data.tags, embedding))
        item_id = cur.fetchone()[0]
        conn.commit()
        return {"item_id": str(item_id), "status": "added", "embedded": embedding is not None}
    except Exception as e:
        logger.error(f"Error adding knowledge: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/files/add")
def add_session_file(data: SessionFile):
    logger.info(f"Adding file: {data.file_path} for session: {data.session_id}")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        content_hash = hashlib.sha256(data.content.encode()).hexdigest()
        embedding = generate_embedding(data.content)
        cur.execute("""
            INSERT INTO session_files (session_id, file_path, file_type, content_hash, content, embedding)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING file_id
        """, (data.session_id, data.file_path, data.file_type, content_hash,
              data.content, embedding))
        file_id = cur.fetchone()[0]
        conn.commit()
        return {"file_id": str(file_id), "content_hash": content_hash,
                "status": "added", "embedded": embedding is not None}
    except Exception as e:
        logger.error(f"Error adding file: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/search")
def search_knowledge(query: str, limit: int = 10):
    logger.info(f"Searching knowledge for: {query[:50]}...")
    conn = None
    try:
        query_embedding = generate_embedding(query)
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT item_id, title, content, tags,
                   1 - (embedding <=> %s::vector) as similarity
            FROM knowledge_items WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector LIMIT %s
        """, (query_embedding, query_embedding, limit))
        results = [{"item_id": str(r[0]), "title": r[1], "content": r[2][:500],
                     "tags": r[3], "similarity": float(r[4])} for r in cur.fetchall()]
        return {"query": query, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


# ===========================================================================
# NEW: Terminal Session Capture Pipeline
# ===========================================================================

@app.post("/sessions/ingest-log")
def ingest_terminal_log(data: TerminalLogIngest):
    """Ingest a raw terminal log: clean, chunk, embed, store, extract entities."""
    logger.info(f"Ingesting terminal log from {data.hostname}/{data.username} ({len(data.raw_log)} bytes)")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cleaned = strip_ansi(data.raw_log)
        started = data.started_at or datetime.utcnow().isoformat()
        ended = data.ended_at or datetime.utcnow().isoformat()

        # Insert session_logs row
        cur.execute("""
            INSERT INTO session_logs (hostname, username, started_at, ended_at, raw_log, cleaned_log)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (data.hostname, data.username, started, ended, data.raw_log, cleaned))
        session_id = cur.fetchone()[0]

        # Chunk and embed
        chunks = chunk_text(cleaned)
        embedded_count = 0
        for i, chunk in enumerate(chunks):
            emb = ollama_embed(chunk)
            if emb:
                embedded_count += 1
            cur.execute("""
                INSERT INTO session_chunks (session_id, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s)
            """, (session_id, i, chunk, emb))

        # Extract entities and upsert concept nodes
        entities = extract_entities(cleaned)
        entity_ids = []
        for ent in entities:
            cur.execute("""
                INSERT INTO concept_nodes (name, node_type)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET metadata = concept_nodes.metadata
                RETURNING id
            """, (ent["name"], ent["node_type"]))
            entity_ids.append(cur.fetchone()[0])

        # Link entities that co-occur in this session
        for i in range(len(entity_ids)):
            for j in range(i + 1, min(i + 5, len(entity_ids))):
                cur.execute("""
                    INSERT INTO concept_edges (source_id, target_id, relationship, session_id)
                    VALUES (%s, %s, 'co_occurs', %s)
                """, (entity_ids[i], entity_ids[j], session_id))

        conn.commit()
        logger.info(f"Ingested session {session_id}: {len(chunks)} chunks, {embedded_count} embedded, {len(entities)} entities")
        return {
            "session_id": str(session_id),
            "chunks": len(chunks),
            "embedded": embedded_count,
            "entities": len(entities),
            "status": "ingested",
        }
    except Exception as e:
        logger.error(f"Error ingesting log: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/sessions/{session_id}/summarize")
def summarize_session(session_id: str):
    """Generate a summary for a stored terminal session using Ollama."""
    logger.info(f"Summarizing session: {session_id}")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT cleaned_log, summary FROM session_logs WHERE id = %s", (session_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

        cleaned_log, existing_summary = row
        if existing_summary:
            return {"session_id": session_id, "summary": existing_summary, "cached": True}

        summary = ollama_summarize(cleaned_log)
        if not summary:
            raise HTTPException(status_code=502, detail="Ollama summarization failed")

        cur.execute("UPDATE session_logs SET summary = %s WHERE id = %s", (summary, session_id))
        conn.commit()
        return {"session_id": session_id, "summary": summary, "cached": False}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error summarizing session: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/sessions/{session_id}/pdf")
def export_session_pdf(session_id: str):
    """Export a session as a formatted PDF."""
    logger.info(f"Exporting PDF for session: {session_id}")
    conn = None
    try:
        from weasyprint import HTML

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT hostname, username, started_at, ended_at, cleaned_log, summary
            FROM session_logs WHERE id = %s
        """, (session_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

        hostname, username, started, ended, log_text, summary = row

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ font-family: 'Courier New', monospace; font-size: 11px; margin: 40px; color: #32374A; }}
h1 {{ font-family: Inter, sans-serif; color: #663399; font-size: 20px; }}
h2 {{ font-family: Inter, sans-serif; color: #32374A; font-size: 14px; margin-top: 20px; }}
.meta {{ font-family: Inter, sans-serif; font-size: 12px; color: #71717A; margin-bottom: 20px; }}
.summary {{ background: #FAF9F7; border-left: 3px solid #663399; padding: 12px; margin: 16px 0; font-family: Inter, sans-serif; font-size: 12px; }}
pre {{ background: #1A1D24; color: #FAF9F7; padding: 16px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; font-size: 10px; line-height: 1.4; }}
</style></head><body>
<h1>Terminal Session Report</h1>
<div class="meta">
  <strong>Host:</strong> {hostname} &nbsp;|&nbsp;
  <strong>User:</strong> {username} &nbsp;|&nbsp;
  <strong>Started:</strong> {started or 'N/A'} &nbsp;|&nbsp;
  <strong>Ended:</strong> {ended or 'N/A'}
</div>
"""
        if summary:
            html += f'<h2>Summary</h2><div class="summary">{summary}</div>'

        escaped_log = (log_text or "No log content").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html += f'<h2>Session Log</h2><pre>{escaped_log}</pre></body></html>'

        pdf_bytes = HTML(string=html).write_pdf()

        import io
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="session-{session_id[:8]}.pdf"'},
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="weasyprint not installed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


# ===========================================================================
# NEW: Knowledge Graph Endpoints
# ===========================================================================

@app.get("/graph/concepts")
def get_concepts(node_type: Optional[str] = None, limit: int = 100):
    """Return concept nodes, optionally filtered by type."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if node_type:
            cur.execute("""
                SELECT id, name, node_type, metadata, created_at
                FROM concept_nodes WHERE node_type = %s
                ORDER BY created_at DESC LIMIT %s
            """, (node_type, limit))
        else:
            cur.execute("""
                SELECT id, name, node_type, metadata, created_at
                FROM concept_nodes ORDER BY created_at DESC LIMIT %s
            """, (limit,))
        nodes = [{"id": str(r[0]), "name": r[1], "node_type": r[2],
                   "metadata": r[3], "created_at": r[4].isoformat() if r[4] else None}
                 for r in cur.fetchall()]
        return {"nodes": nodes, "count": len(nodes)}
    except Exception as e:
        logger.error(f"Error fetching concepts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/graph/edges")
def get_edges(node_id: Optional[str] = None, limit: int = 200):
    """Return concept edges, optionally filtered to a specific node."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if node_id:
            cur.execute("""
                SELECT e.id, s.name as source, t.name as target,
                       e.relationship, e.weight, e.session_id
                FROM concept_edges e
                JOIN concept_nodes s ON e.source_id = s.id
                JOIN concept_nodes t ON e.target_id = t.id
                WHERE e.source_id = %s OR e.target_id = %s
                ORDER BY e.created_at DESC LIMIT %s
            """, (node_id, node_id, limit))
        else:
            cur.execute("""
                SELECT e.id, s.name as source, t.name as target,
                       e.relationship, e.weight, e.session_id
                FROM concept_edges e
                JOIN concept_nodes s ON e.source_id = s.id
                JOIN concept_nodes t ON e.target_id = t.id
                ORDER BY e.created_at DESC LIMIT %s
            """, (limit,))
        edges = [{"id": str(r[0]), "source": r[1], "target": r[2],
                  "relationship": r[3], "weight": r[4],
                  "session_id": str(r[5]) if r[5] else None}
                 for r in cur.fetchall()]
        return {"edges": edges, "count": len(edges)}
    except Exception as e:
        logger.error(f"Error fetching edges: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/graph/link")
def link_concepts(data: ConceptLink):
    """Manually link two concepts in the knowledge graph."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Upsert both nodes
        for name, ntype in [(data.source_name, data.source_type), (data.target_name, data.target_type)]:
            cur.execute("""
                INSERT INTO concept_nodes (name, node_type)
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING
            """, (name, ntype))

        cur.execute("SELECT id FROM concept_nodes WHERE name = %s", (data.source_name,))
        source_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM concept_nodes WHERE name = %s", (data.target_name,))
        target_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO concept_edges (source_id, target_id, relationship, session_id)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (source_id, target_id, data.relationship,
              data.session_id if data.session_id else None))
        edge_id = cur.fetchone()[0]
        conn.commit()
        return {"edge_id": str(edge_id), "source": data.source_name,
                "target": data.target_name, "relationship": data.relationship}
    except Exception as e:
        logger.error(f"Error linking concepts: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


# ===========================================================================
# NEW: Semantic search across session chunks (Ollama embeddings)
# ===========================================================================

@app.post("/sessions/search")
def search_sessions(query: str, limit: int = 10):
    """Semantic search across terminal session chunks using Ollama embeddings."""
    logger.info(f"Searching sessions for: {query[:50]}...")
    conn = None
    try:
        query_emb = ollama_embed(query)
        if not query_emb:
            raise HTTPException(status_code=502, detail="Failed to generate query embedding via Ollama")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.session_id, c.chunk_index, c.content,
                   sl.hostname, sl.summary,
                   1 - (c.embedding <=> %s::vector) as similarity
            FROM session_chunks c
            JOIN session_logs sl ON c.session_id = sl.id
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """, (query_emb, query_emb, limit))
        results = [{"chunk_id": str(r[0]), "session_id": str(r[1]),
                     "chunk_index": r[2], "content": r[3][:500],
                     "hostname": r[4], "summary": r[5],
                     "similarity": float(r[6])} for r in cur.fetchall()]
        return {"query": query, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


# ===========================================================================
# List sessions
# ===========================================================================

@app.get("/sessions/logs")
def list_session_logs(limit: int = 50):
    """List recent terminal session logs."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, hostname, username, started_at, ended_at, summary,
                   length(raw_log) as log_size
            FROM session_logs ORDER BY created_at DESC LIMIT %s
        """, (limit,))
        sessions = [{"id": str(r[0]), "hostname": r[1], "username": r[2],
                      "started_at": r[3].isoformat() if r[3] else None,
                      "ended_at": r[4].isoformat() if r[4] else None,
                      "summary": r[5], "log_size_bytes": r[6]}
                    for r in cur.fetchall()]
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


# ===========================================================================
# Stats Endpoints
# ===========================================================================

@app.get("/sessions/stats/overview")
def stats_overview():
    """Aggregated overview: totals, averages, date range, embedding coverage."""
    conn = None
    start_time = time.time()
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                (SELECT count(*) FROM session_logs)   AS total_sessions,
                (SELECT count(*) FROM session_chunks)  AS total_chunks,
                (SELECT count(*) FROM concept_nodes)   AS total_concepts,
                (SELECT count(*) FROM concept_edges)   AS total_edges,
                (SELECT count(*) FILTER (WHERE embedding IS NOT NULL)
                    FROM session_chunks)               AS embedded_chunks,
                (SELECT min(created_at) FROM session_logs) AS earliest,
                (SELECT max(created_at) FROM session_logs) AS latest
        """)
        row = cur.fetchone()
        total_sessions, total_chunks, total_concepts, total_edges, \
            embedded_chunks, earliest, latest = row

        avg_chunks = total_chunks / total_sessions if total_sessions > 0 else 0.0
        embedding_pct = (embedded_chunks * 100.0 / total_chunks) if total_chunks > 0 else 0.0

        session_logger_read_operations.labels(operation='stats_overview').inc()
        session_logger_read_latency.labels(operation='stats_overview').observe(
            (time.time() - start_time) * 1000)

        return StatsOverview(
            total_sessions=total_sessions,
            total_chunks=total_chunks,
            total_concepts=total_concepts,
            total_edges=total_edges,
            avg_chunks_per_session=round(avg_chunks, 2),
            embedding_coverage_pct=round(embedding_pct, 2),
            earliest_session=earliest.isoformat() if earliest else None,
            latest_session=latest.isoformat() if latest else None,
        )
    except Exception as e:
        session_logger_errors.labels(error_type='stats_overview_failed').inc()
        logger.error(f"Error fetching stats overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch stats overview")
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/sessions/stats/daily")
def stats_daily():
    """Session count per day for the last 7 days, including zero-count days."""
    conn = None
    start_time = time.time()
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT d::date AS day,
                   coalesce(count(sl.id), 0) AS session_count
            FROM generate_series(
                current_date - interval '6 days',
                current_date,
                interval '1 day'
            ) AS d
            LEFT JOIN session_logs sl
                ON date_trunc('day', sl.created_at) = d::date
            GROUP BY d::date
            ORDER BY d::date
        """)
        rows = cur.fetchall()

        days = [
            DailySessionCount(
                date=row[0].isoformat(),
                session_count=row[1],
            )
            for row in rows
        ]

        session_logger_read_operations.labels(operation='stats_daily').inc()
        session_logger_read_latency.labels(operation='stats_daily').observe(
            (time.time() - start_time) * 1000)

        return DailyStats(
            days=days,
            period_start=(rows[0][0].isoformat() if rows else ""),
            period_end=(rows[-1][0].isoformat() if rows else ""),
        )
    except Exception as e:
        session_logger_errors.labels(error_type='stats_daily_failed').inc()
        logger.error(f"Error fetching daily stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch daily stats")
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/sessions/stats/concepts")
def stats_concepts(limit: int = 10):
    """Top concepts by edge count, node type breakdown, and totals."""
    conn = None
    start_time = time.time()
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT cn.name, cn.node_type, count(*) AS edge_count
            FROM concept_nodes cn
            JOIN (
                SELECT source_id AS node_id FROM concept_edges
                UNION ALL
                SELECT target_id AS node_id FROM concept_edges
            ) edges ON edges.node_id = cn.id
            GROUP BY cn.id, cn.name, cn.node_type
            ORDER BY edge_count DESC
            LIMIT %s
        """, (limit,))
        top_concepts = [
            ConceptRanking(name=row[0], node_type=row[1], edge_count=row[2])
            for row in cur.fetchall()
        ]

        cur.execute("""
            SELECT node_type, count(*) AS cnt
            FROM concept_nodes
            GROUP BY node_type
            ORDER BY cnt DESC
        """)
        type_breakdown = [
            NodeTypeBreakdown(node_type=row[0], count=row[1])
            for row in cur.fetchall()
        ]

        cur.execute("SELECT count(*) FROM concept_nodes")
        total_nodes = cur.fetchone()[0]

        cur.execute("SELECT count(*) FROM concept_edges")
        total_edges = cur.fetchone()[0]

        session_logger_read_operations.labels(operation='stats_concepts').inc()
        session_logger_read_latency.labels(operation='stats_concepts').observe(
            (time.time() - start_time) * 1000)

        return ConceptStats(
            top_concepts=top_concepts,
            node_type_breakdown=type_breakdown,
            total_nodes=total_nodes,
            total_edges=total_edges,
        )
    except Exception as e:
        session_logger_errors.labels(error_type='stats_concepts_failed').inc()
        logger.error(f"Error fetching concept stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch concept stats")
    finally:
        if conn:
            return_db_connection(conn)


# ===========================================================================
# Backfill embeddings
# ===========================================================================

@app.post("/backfill-embeddings")
def backfill_embeddings():
    """Generate Ollama embeddings for all rows missing them across all tables."""
    logger.info("Starting embedding backfill")
    conn = None
    results = {}
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # knowledge_items
        cur.execute("SELECT item_id, title, content FROM knowledge_items WHERE embedding IS NULL")
        rows = cur.fetchall()
        count = 0
        for item_id, title, content in rows:
            emb = ollama_embed(f"{title}\n\n{content}")
            if emb:
                cur.execute("UPDATE knowledge_items SET embedding = %s WHERE item_id = %s", (emb, item_id))
                count += 1
        results["knowledge_items"] = count

        # session_chunks
        cur.execute("SELECT id, content FROM session_chunks WHERE embedding IS NULL")
        rows = cur.fetchall()
        count = 0
        for chunk_id, content in rows:
            emb = ollama_embed(content)
            if emb:
                cur.execute("UPDATE session_chunks SET embedding = %s WHERE id = %s", (emb, chunk_id))
                count += 1
        results["session_chunks"] = count

        # ai_sessions
        cur.execute("SELECT session_id, summary FROM ai_sessions WHERE embedding IS NULL AND summary IS NOT NULL")
        rows = cur.fetchall()
        count = 0
        for sid, summary in rows:
            emb = ollama_embed(summary)
            if emb:
                cur.execute("UPDATE ai_sessions SET embedding = %s WHERE session_id = %s", (emb, sid))
                count += 1
        results["ai_sessions"] = count

        # session_files
        cur.execute("SELECT file_id, content FROM session_files WHERE embedding IS NULL")
        rows = cur.fetchall()
        count = 0
        for fid, content in rows:
            emb = ollama_embed(content)
            if emb:
                cur.execute("UPDATE session_files SET embedding = %s WHERE file_id = %s", (emb, fid))
                count += 1
        results["session_files"] = count

        conn.commit()
        total = sum(results.values())
        logger.info(f"Backfill complete: {total} embeddings generated")
        return {"status": "complete", "embedded": results, "total": total}
    except Exception as e:
        logger.error(f"Backfill error: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            return_db_connection(conn)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting DHG Session Logger v2.0.0")
    uvicorn.run(app, host="0.0.0.0", port=8009)
