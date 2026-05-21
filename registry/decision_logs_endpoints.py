"""Decision Logs API endpoints.

Routes:
  POST   /api/decision-logs          create a decision log
  GET    /api/decision-logs          list with filters (project_name, domain, limit, offset)
  POST   /api/decision-logs/search   full-text search across decision logs
  DELETE /api/decision-logs/{item_id} delete a decision log
"""
import os
import sys
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from decision_logs_schemas import (
    DecisionLogCreate,
    DecisionLogResponse,
    DecisionLogList,
    DecisionLogSearch,
)
import decision_logs_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/decision-logs", tags=["decision-logs"])


@router.post("", response_model=DecisionLogResponse, status_code=status.HTTP_201_CREATED)
async def create_decision_log(
    payload: DecisionLogCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> DecisionLogResponse:
    start = time.time()
    try:
        embedding = None
        try:
            from embedding_utils import get_embedding
            text_for_embed = f"{payload.title} {payload.choice} {payload.rationale}"
            embedding = await get_embedding(text_for_embed)
        except Exception as embed_err:
            logger.warning("Embedding generation failed: %s", embed_err)

        row, created = svc.upsert_decision_log(db, payload, embedding)

        if not created:
            response.status_code = status.HTTP_200_OK

        registry_write_operations.labels(operation="create_decision_log").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_decision_log_failed").inc()
        logger.error("create_decision_log failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=DecisionLogList)
async def list_decision_logs(
    project_name: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> DecisionLogList:
    start = time.time()
    try:
        rows, total = svc.list_decision_logs(
            db, project_name=project_name, domain=domain,
            limit=limit, offset=offset,
        )

        registry_read_operations.labels(operation="list_decision_logs").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DecisionLogList(decision_logs=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_decision_logs_failed").inc()
        logger.error("%s failed: %s", "decision_logs_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=DecisionLogList)
async def search_decision_logs(
    body: DecisionLogSearch,
    db: Session = Depends(get_db),
) -> DecisionLogList:
    start = time.time()
    try:
        rows, total = svc.search_decision_logs(
            db, body.query,
            project_name=body.project_name, domain=body.domain,
            limit=body.limit,
        )

        registry_read_operations.labels(operation="search_decision_logs").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DecisionLogList(decision_logs=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="search_decision_logs_failed").inc()
        logger.error("%s failed: %s", "decision_logs_op", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_decision_log(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        row = svc.delete_decision_log(db, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="delete_decision_log_failed").inc()
        logger.error("delete_decision_log failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
