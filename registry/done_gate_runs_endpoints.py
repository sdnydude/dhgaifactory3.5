"""Done-gate runs API endpoints — Loop 4 done-gate verdict ledger.

Routes:
  POST   /api/done-gate-runs                     capture a claim-bearing gate run
  GET    /api/done-gate-runs                     list with filters (project/verdict/adjudicated)
  GET    /api/done-gate-runs/stats               per-check_version precision rollup
  PATCH  /api/done-gate-runs/{item_id}/adjudicate  operator ratchet input (tp/fp/fn)

Client half lives in dhg-memreg (hooks/done-gate.py, observe-only Stop hook).
Pre-registered in dhg-harness/LOOP-CLOSURE-RESEARCH-PROTOCOL.md §12 (v1.1, locked).
"""
import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from done_gate_runs_schemas import (
    DoneGateRunCreate,
    DoneGateRunAdjudicate,
    DoneGateRunResponse,
    DoneGateRunList,
    DoneGateStatsResponse,
    VALID_VERDICTS,
    VALID_ADJUDICATIONS,
)
import done_gate_runs_service as svc

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
)


router = APIRouter(prefix="/api/done-gate-runs", tags=["done-gate-runs"])


@router.post("", response_model=DoneGateRunResponse, status_code=201)
async def create_run(
    payload: DoneGateRunCreate,
    db: Session = Depends(get_db),
):
    start = time.time()
    if payload.verdict not in VALID_VERDICTS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid verdict '{payload.verdict}'. Valid: {sorted(VALID_VERDICTS)}",
        )
    try:
        row = svc.create_run(db, payload)

        registry_write_operations.labels(operation="create_done_gate_run").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="create_done_gate_run_failed").inc()
        logger.error("create_done_gate_run failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=DoneGateRunList)
async def list_runs(
    project: Optional[str] = Query(None),
    verdict: Optional[str] = Query(None),
    adjudicated: Optional[bool] = Query(
        None, description="true = adjudicated rows only, false = pending only"),
    check_version: Optional[int] = Query(None, ge=1),
    sampled: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    start = time.time()
    try:
        rows, total = svc.list_runs(
            db, project=project, verdict=verdict, adjudicated=adjudicated,
            check_version=check_version, sampled=sampled,
            limit=limit, offset=offset,
        )

        registry_read_operations.labels(operation="list_done_gate_runs").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DoneGateRunList(runs=rows, total=total)
    except Exception as e:
        registry_errors.labels(error_type="list_done_gate_runs_failed").inc()
        logger.error("list_done_gate_runs failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats", response_model=DoneGateStatsResponse)
async def done_gate_stats(
    project: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    start = time.time()
    try:
        versions = svc.stats(db, project=project)

        registry_read_operations.labels(operation="done_gate_stats").inc()
        registry_read_latency.observe((time.time() - start) * 1000)
        return DoneGateStatsResponse(project=project, versions=versions)
    except Exception as e:
        registry_errors.labels(error_type="done_gate_stats_failed").inc()
        logger.error("done_gate_stats failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{item_id}/adjudicate", response_model=DoneGateRunResponse)
async def adjudicate_run(
    item_id: UUID,
    payload: DoneGateRunAdjudicate,
    db: Session = Depends(get_db),
):
    start = time.time()
    if payload.adjudication not in VALID_ADJUDICATIONS:
        raise HTTPException(
            status_code=422,
            detail=(f"Invalid adjudication '{payload.adjudication}'. "
                    f"Valid: {sorted(VALID_ADJUDICATIONS)}"),
        )
    try:
        row = svc.adjudicate_run(db, item_id, payload.adjudication)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")

        registry_write_operations.labels(operation="adjudicate_done_gate_run").inc()
        registry_write_latency.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="adjudicate_done_gate_run_failed").inc()
        logger.error("adjudicate_done_gate_run failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
