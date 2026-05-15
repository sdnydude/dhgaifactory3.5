"""Insights API endpoints.

Routes:
  POST   /api/insights          create an insight
  GET    /api/insights          list with filters (project_name, category, limit, offset)
  GET    /api/insights/search   full-text search across insights
"""
import os
import sys
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from models import Insight
from insights_schemas import (
    InsightCreate,
    InsightResponse,
    InsightList,
    InsightSearch,
)

logger = logging.getLogger(__name__)

try:
    from api import (
        registry_read_latency,
        registry_read_operations,
        registry_write_latency,
        registry_write_operations,
        registry_errors,
    )
except ImportError:
    from prometheus_client import Counter, Histogram
    registry_read_latency = Histogram(
        "registry_read_latency", "Read latency",
        buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
    )
    registry_read_operations = Counter(
        "registry_read_operations", "Read operations", ["operation"],
    )
    registry_write_latency = Histogram(
        "registry_write_latency", "Write latency",
        buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
    )
    registry_write_operations = Counter(
        "registry_write_operations", "Write operations", ["operation"],
    )
    registry_errors = Counter(
        "registry_errors", "Registry errors", ["error_type"],
    )


router = APIRouter(prefix="/api/insights", tags=["insights"])


def _upsert_insight(
    db: Session, payload: InsightCreate, embedding=None,
) -> tuple[Insight, bool]:
    """Upsert by (project_name, tldr). Returns (row, created)."""
    existing = db.query(Insight).filter(
        Insight.project_name == payload.project_name,
        Insight.tldr == payload.tldr,
    ).first()

    if existing:
        existing.insight_statement = payload.insight_statement
        existing.category = payload.category
        existing.subcategory = payload.subcategory
        existing.source_file = payload.source_file
        existing.source_language = payload.source_language
        existing.source_framework = payload.source_framework
        existing.tags = payload.tags
        existing.session_id = payload.session_id
        existing.model_name = payload.model_name
        existing.meta_data = payload.meta_data
        if embedding:
            existing.embedding = embedding
            existing.embedding_model = "nomic-embed-text"
        return existing, False

    row = Insight(**payload.model_dump())
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
        return row, True
    except IntegrityError:
        db.rollback()
        existing = db.query(Insight).filter(
            Insight.project_name == payload.project_name,
            Insight.tldr == payload.tldr,
        ).first()
        if existing:
            existing.insight_statement = payload.insight_statement
            existing.category = payload.category
            existing.subcategory = payload.subcategory
            existing.source_file = payload.source_file
            existing.source_language = payload.source_language
            existing.source_framework = payload.source_framework
            existing.tags = payload.tags
            existing.session_id = payload.session_id
            existing.model_name = payload.model_name
            existing.meta_data = payload.meta_data
            if embedding:
                existing.embedding = embedding
                existing.embedding_model = "nomic-embed-text"
            return existing, False
        raise


@router.post("", response_model=InsightResponse, status_code=status.HTTP_201_CREATED)
async def create_insight(
    payload: InsightCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> InsightResponse:
    start = time.time()
    try:
        embedding = None
        try:
            from embedding_utils import get_embedding
            text_for_embed = f"{payload.tldr} {payload.insight_statement}"
            embedding = await get_embedding(text_for_embed)
        except Exception as embed_err:
            logger.warning("Embedding generation failed: %s", embed_err)

        row, created = _upsert_insight(db, payload, embedding)
        db.commit()
        db.refresh(row)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="create_insight").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_insight_failed").inc()
        logger.error("%s failed: %s", "insights_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=InsightList)
async def list_insights(
    project_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> InsightList:
    start = time.time()
    try:
        query = db.query(Insight)
        if project_name:
            query = query.filter(Insight.project_name == project_name)
        if category:
            query = query.filter(Insight.category == category)

        total = query.count()
        rows = (
            query
            .order_by(Insight.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        registry_read_operations.labels(operation="list_insights").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return InsightList(insights=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_insights_failed").inc()
        logger.error("%s failed: %s", "insights_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=InsightList)
async def search_insights(
    body: InsightSearch,
    db: Session = Depends(get_db),
) -> InsightList:
    start = time.time()
    try:
        ts_query = sa_func.plainto_tsquery("english", body.query)
        query = (
            db.query(Insight)
            .filter(Insight.search_vector.op("@@")(ts_query))
        )
        if body.project_name:
            query = query.filter(Insight.project_name == body.project_name)
        if body.category:
            query = query.filter(Insight.category == body.category)

        total = query.count()
        rows = (
            query
            .order_by(sa_func.ts_rank(Insight.search_vector, ts_query).desc())
            .limit(body.limit)
            .all()
        )

        registry_read_operations.labels(operation="search_insights").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return InsightList(insights=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_insights_failed").inc()
        logger.error("%s failed: %s", "insights_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insight(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = db.query(Insight).filter(Insight.id == item_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(row)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_insight_failed").inc()
        logger.error("delete_insight failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
