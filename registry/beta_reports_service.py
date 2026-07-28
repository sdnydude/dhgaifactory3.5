"""Beta Reports service layer — all database operations for beta_reports."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from models import BetaReport
from beta_reports_schemas import BetaReportCreate, BetaReportUpdate

logger = logging.getLogger(__name__)


def create_beta_report(db: Session, payload: BetaReportCreate) -> BetaReport:
    row = BetaReport(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_beta_reports(
    db: Session,
    *,
    project_name: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[BetaReport], int]:
    query = db.query(BetaReport)
    if project_name:
        query = query.filter(BetaReport.project_name == project_name)
    if status:
        query = query.filter(BetaReport.status == status)
    if severity:
        query = query.filter(BetaReport.severity == severity)

    total = query.count()
    rows = (
        query
        .order_by(BetaReport.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def update_beta_report(db: Session, report_id: UUID, payload: BetaReportUpdate) -> BetaReport | None:
    row = db.query(BetaReport).filter(BetaReport.id == report_id).first()
    if not row:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
