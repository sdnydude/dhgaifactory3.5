"""CME stats endpoints — aggregate telemetry for Mission Control dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user, AuthenticatedUser
from database import get_db
import cme_stats_service as svc

router = APIRouter(prefix="/api/cme/stats", tags=["cme-stats"])


@router.get("/pipeline")
def pipeline_stats(
    db: Session = Depends(get_db),
    _user: AuthenticatedUser = Depends(get_current_user),
):
    return svc.get_pipeline_stats(db)


@router.get("/services")
def service_health(
    db: Session = Depends(get_db),
    _user: AuthenticatedUser = Depends(get_current_user),
):
    return svc.get_service_health(db)
