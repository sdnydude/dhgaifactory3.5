"""
Unified Search API for all data sources.

Searches across:
- ChatGPT conversations
- Claude conversations
- Gemini conversations
- Antigravity sessions
- Gmail emails
- Google Drive documents
- Documentation pages (doc_pages)
"""
import logging
from typing import NamedTuple, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from embedding_utils import get_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


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


class SourceTable(NamedTuple):
    table: str
    display_name: str
    content_col: str
    timestamp_col: str
    title_col: str
    id_col: str
    has_user_id: bool


SOURCE_TABLES: dict[str, SourceTable] = {
    "chatgpt": SourceTable("chatgpt_messages", "ChatGPT", "content", "timestamp", "role", "conversation_id", True),
    "claude": SourceTable("claude_messages", "Claude", "content", "timestamp", "role", "conversation_id", True),
    "gemini": SourceTable("gemini_messages", "Gemini", "content", "timestamp", "role", "conversation_id", True),
    "antigravity": SourceTable("antigravity_messages", "Antigravity", "content", "timestamp", "role", "conversation_id", True),
    "gmail": SourceTable("gws_emails", "Gmail", "body_text", "date", "subject", "message_id", True),
    "gdrive": SourceTable("gws_documents", "Google Drive", "content_text", "last_modified", "title", "drive_id", True),
    "docs": SourceTable("doc_pages", "Documentation", "content", "created_at", "title", "id", False),
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

    table, display_name, content_col, ts_col, title_col, id_col, has_user_id = SOURCE_TABLES[source_key]
    embedding_str = str(query_embedding)

    user_filter = "user_id = :uid AND" if has_user_id else ""
    sql = text(f"""
        SELECT {content_col}, {ts_col}, 1 - (embedding <=> CAST(:emb AS vector)) as score,
               {title_col}, {id_col}
        FROM {table}
        WHERE {user_filter} embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT :lim
    """)

    results = []
    try:
        params = {"emb": embedding_str, "lim": limit}
        if has_user_id:
            params["uid"] = user_id
        rows = db.execute(sql, params).fetchall()
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
        logger.warning("Error searching %s: %s", table, e)

    return results


@router.get("", response_model=SearchResponse)
async def unified_search(
    query: str = Query(..., min_length=3, description="Search query"),
    user_id: str = Query(..., description="User UUID"),
    sources: Optional[str] = Query(
        None,
        description="Comma-separated sources: chatgpt,claude,gemini,antigravity,gmail,gdrive,docs"
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
    user_tables = [
        ("chatgpt_messages", "ChatGPT"),
        ("claude_messages", "Claude"),
        ("gemini_messages", "Gemini"),
        ("antigravity_messages", "Antigravity"),
        ("gws_emails", "Gmail"),
        ("gws_documents", "Google Drive"),
        ("gws_calendar", "Google Calendar"),
    ]
    shared_tables = [
        ("doc_pages", "Documentation"),
    ]

    for table, display_name in user_tables:
        try:
            result = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar()
            sources_info[display_name] = {"table": table, "count": result}
        except Exception as e:
            db.rollback()
            logger.exception("search source %s unavailable", table)
            sources_info[display_name] = {"table": table, "count": 0, "error": "unavailable"}

    for table, display_name in shared_tables:
        try:
            result = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            sources_info[display_name] = {"table": table, "count": result}
        except Exception as e:
            db.rollback()
            logger.exception("search source %s unavailable", table)
            sources_info[display_name] = {"table": table, "count": 0, "error": "unavailable"}

    return {"user_id": user_id, "sources": sources_info}
