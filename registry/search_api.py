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

import httpx
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

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


async def get_embedding(text_input: str) -> Optional[list]:
    """Get embedding from Ollama using async httpx."""
    if not text_input:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{OLLAMA_URL}/api/embeddings',
                json={'model': EMBED_MODEL, 'prompt': text_input},
            )
            if response.status_code == 200:
                return response.json().get('embedding')
    except Exception as e:
        logger.warning(f"Embedding error: {e}")
    return None


# Table config: (table_name, display_name, content_col, timestamp_col, title_col, id_col)
SOURCE_TABLES = {
    "chatgpt": ("chatgpt_messages", "ChatGPT", "content", "timestamp", "role", "conversation_id"),
    "claude": ("claude_messages", "Claude", "content", "timestamp", "role", "conversation_id"),
    "gemini": ("gemini_messages", "Gemini", "content", "timestamp", "role", "conversation_id"),
    "antigravity": ("antigravity_messages", "Antigravity", "content", "timestamp", "role", "conversation_id"),
    "gmail": ("gws_emails", "Gmail", "body_text", "date", "subject", "message_id"),
    "gdrive": ("gws_documents", "Google Drive", "content_text", "last_modified", "title", "drive_id"),
}


def search_table(
    db: Session,
    source_key: str,
    query_embedding: list,
    user_id: str,
    limit: int = 5,
) -> list[SearchResult]:
    """Search a single table by embedding similarity using the shared ORM session."""
    if source_key not in SOURCE_TABLES:
        return []

    table, display_name, content_col, ts_col, title_col, id_col = SOURCE_TABLES[source_key]
    embedding_str = str(query_embedding)

    sql = text(f"""
        SELECT {content_col}, {ts_col}, 1 - (embedding <=> CAST(:emb AS vector)) as score,
               {title_col}, {id_col}
        FROM {table}
        WHERE user_id = :uid AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT :lim
    """)

    results = []
    try:
        rows = db.execute(sql, {"emb": embedding_str, "uid": user_id, "lim": limit}).fetchall()
        for row in rows:
            content, timestamp, score, title_or_role, id_field = row
            content_preview = content[:500] + "..." if len(content) > 500 else content
            results.append(SearchResult(
                source=display_name,
                content=content_preview,
                score=float(score),
                title=title_or_role,
                timestamp=str(timestamp) if timestamp else None,
                metadata={"id": str(id_field)},
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
    db: Session = Depends(get_db),
):
    """Search across all data sources using semantic similarity."""
    all_sources = list(SOURCE_TABLES.keys())
    if sources:
        selected = [s.strip().lower() for s in sources.split(",")]
        selected = [s for s in selected if s in all_sources]
    else:
        selected = all_sources

    if not selected:
        raise HTTPException(400, "No valid sources specified")

    query_embedding = await get_embedding(query)
    if not query_embedding:
        raise HTTPException(500, "Failed to generate query embedding")

    all_results = []
    for source in selected:
        results = search_table(db, source, query_embedding, user_id, limit)
        all_results.extend(results)

    all_results.sort(key=lambda x: x.score, reverse=True)
    all_results = all_results[:limit * 2]

    return SearchResponse(
        query=query,
        results=all_results,
        total=len(all_results),
    )


@router.get("/sources")
async def list_sources(user_id: str, db: Session = Depends(get_db)):
    """List available sources and their document counts for a user."""
    sources_info = {}
    all_tables = [
        ("chatgpt_messages", "ChatGPT"),
        ("claude_messages", "Claude"),
        ("gemini_messages", "Gemini"),
        ("antigravity_messages", "Antigravity"),
        ("gws_emails", "Gmail"),
        ("gws_documents", "Google Drive"),
        ("gws_calendar", "Google Calendar"),
    ]

    for table, display_name in all_tables:
        try:
            result = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar()
            sources_info[display_name] = {"table": table, "count": result}
        except Exception as e:
            sources_info[display_name] = {"table": table, "count": 0, "error": str(e)}

    return {"user_id": user_id, "sources": sources_info}
