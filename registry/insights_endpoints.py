"""Insights API endpoints.

Routes:
  POST   /api/insights          create an insight
  GET    /api/insights          list with filters (project_name, category, limit, offset)
  POST   /api/insights/search   full-text search across insights
  DELETE /api/insights/{item_id} delete an insight
"""
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from database import get_db
from insights_schemas import (
    InsightCreate,
    InsightResponse,
    InsightList,
    InsightSearch,
)
import insights_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/insights", tags=["insights"])


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

        row, created = svc.upsert_insight(db, payload, embedding)

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
        rows, total = svc.list_insights(
            db, project_name=project_name, category=category,
            limit=limit, offset=offset,
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
        rows, total = svc.search_insights(
            db, body.query,
            project_name=body.project_name, category=body.category,
            limit=body.limit,
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
        row = svc.delete_insight(db, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_insight_failed").inc()
        logger.error("delete_insight failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
