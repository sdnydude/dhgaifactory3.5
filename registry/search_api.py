"""
Unified Search API for all data sources.

Searches across:
- ChatGPT conversations
- Claude conversations
- Gemini conversations
- Antigravity sessions
- Gmail emails
- Google Drive documents
"""
import logging
import os
from typing import Optional

import psycopg2
import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

# Database connection
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_USER = os.getenv('POSTGRES_USER', 'dhg')
DB_PASS = os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', ''))
DB_NAME = os.getenv('POSTGRES_DB', 'dhg_registry')

# Ollama for embeddings
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
EMBED_MODEL = os.getenv('EMBED_MODEL', 'nomic-embed-text')


class SearchResult(BaseModel):
    """Individual search result."""
    source: str
    content: str
    score: float
    title: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Optional[dict] = None


class SearchResponse(BaseModel):
    """Search response with results."""
    query: str
    results: list[SearchResult]
    total: int


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )


def get_embedding(text: str) -> Optional[list]:
    """Get embedding from Ollama."""
    if not text:
        return None
    try:
        response = requests.post(
            f'{OLLAMA_URL}/api/embeddings',
            json={'model': EMBED_MODEL, 'prompt': text},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get('embedding')
    except Exception as e:
        logger.warning(f"Embedding error: {e}")
    return None


def search_table(
    cur, 
    table: str, 
    source_name: str,
    query_embedding: list, 
    user_id: str,
    limit: int = 5
) -> list[SearchResult]:
    """Search a single table by embedding similarity."""
    results = []
    
    # Build query based on table type
    if table.endswith('_messages'):
        sql = f"""
            SELECT content, timestamp, 1 - (embedding <=> %s::vector) as score,
                   role, conversation_id
            FROM {table}
            WHERE user_id = %s AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
    elif table == 'gws_emails':
        sql = f"""
            SELECT body_text, date, 1 - (embedding <=> %s::vector) as score,
                   subject, message_id
            FROM {table}
            WHERE user_id = %s AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
    elif table == 'gws_documents':
        sql = f"""
            SELECT content_text, last_modified, 1 - (embedding <=> %s::vector) as score,
                   title, drive_id
            FROM {table}
            WHERE user_id = %s AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
    else:
        return results
    
    try:
        embedding_str = str(query_embedding)
        cur.execute(sql, (embedding_str, user_id, embedding_str, limit))
        
        for row in cur.fetchall():
            content, timestamp, score, title_or_role, id_field = row
            
            # Truncate content for response
            content_preview = content[:500] + "..." if len(content) > 500 else content
            
            results.append(SearchResult(
                source=source_name,
                content=content_preview,
                score=float(score),
                title=title_or_role,
                timestamp=str(timestamp) if timestamp else None,
                metadata={"id": str(id_field)}
            ))
    except Exception as e:
        logger.warning(f"Error searching {table}: {e}")
    
    return results


@router.get("", response_model=SearchResponse)
async def unified_search(
    query: str = Query(..., min_length=3, description="Search query"),
    user_id: str = Query(..., description="User UUID"),
    sources: Optional[str] = Query(
        None, 
        description="Comma-separated sources: chatgpt,claude,gemini,antigravity,gmail,gdrive"
    ),
    limit: int = Query(10, ge=1, le=50, description="Max results per source"),
):
    """
    Search across all data sources using semantic similarity.
    
    Returns ranked results from all specified sources.
    """
    # Parse sources
    all_sources = ["chatgpt", "claude", "gemini", "antigravity", "gmail", "gdrive"]
    if sources:
        selected = [s.strip().lower() for s in sources.split(",")]
        selected = [s for s in selected if s in all_sources]
    else:
        selected = all_sources
    
    if not selected:
        raise HTTPException(400, "No valid sources specified")
    
    # Get query embedding
    query_embedding = get_embedding(query)
    if not query_embedding:
        raise HTTPException(500, "Failed to generate query embedding")
    
    # Map sources to tables
    source_tables = {
        "chatgpt": ("chatgpt_messages", "ChatGPT"),
        "claude": ("claude_messages", "Claude"),
        "gemini": ("gemini_messages", "Gemini"),
        "antigravity": ("antigravity_messages", "Antigravity"),
        "gmail": ("gws_emails", "Gmail"),
        "gdrive": ("gws_documents", "Google Drive"),
    }
    
    # Search all sources
    all_results = []
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        for source in selected:
            if source in source_tables:
                table, display_name = source_tables[source]
                results = search_table(cur, table, display_name, query_embedding, user_id, limit)
                all_results.extend(results)
    finally:
        cur.close()
        conn.close()
    
    # Sort by score descending
    all_results.sort(key=lambda x: x.score, reverse=True)
    
    # Limit total results
    all_results = all_results[:limit * 2]  # Return up to 2x limit total
    
    return SearchResponse(
        query=query,
        results=all_results,
        total=len(all_results)
    )


@router.get("/sources")
async def list_sources(user_id: str):
    """List available sources and their document counts for a user."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    sources = {}
    tables = [
        ("chatgpt_messages", "ChatGPT"),
        ("claude_messages", "Claude"),
        ("gemini_messages", "Gemini"),
        ("antigravity_messages", "Antigravity"),
        ("gws_emails", "Gmail"),
        ("gws_documents", "Google Drive"),
        ("gws_calendar", "Google Calendar"),
    ]
    
    for table, display_name in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = %s", (user_id,))
            count = cur.fetchone()[0]
            sources[display_name] = {"table": table, "count": count}
        except Exception as e:
            sources[display_name] = {"table": table, "count": 0, "error": str(e)}
    
    cur.close()
    conn.close()
    
    return {"user_id": user_id, "sources": sources}
