"""Done-gate runs service layer — all database operations for done_gate_runs."""
from __future__ import annotations

import logging

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from models import DoneGateRun
from done_gate_runs_schemas import DoneGateRunCreate

logger = logging.getLogger(__name__)


def create_run(db: Session, payload: DoneGateRunCreate) -> DoneGateRun:
    row = DoneGateRun(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_runs(
    db: Session,
    *,
    project: str | None = None,
    verdict: str | None = None,
    adjudicated: bool | None = None,
    check_version: int | None = None,
    sampled: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DoneGateRun], int]:
    q = db.query(DoneGateRun)
    if project:
        q = q.filter(DoneGateRun.project == project)
    if verdict:
        q = q.filter(DoneGateRun.verdict == verdict)
    if adjudicated is True:
        q = q.filter(DoneGateRun.adjudication.isnot(None))
    elif adjudicated is False:
        q = q.filter(DoneGateRun.adjudication.is_(None))
    if check_version is not None:
        q = q.filter(DoneGateRun.check_version == check_version)
    if sampled is not None:
        q = q.filter(DoneGateRun.sampled == sampled)

    total = q.count()
    rows = q.order_by(DoneGateRun.created_at.desc()).offset(offset).limit(limit).all()
    return rows, total


def stats(db: Session, *, project: str | None = None) -> list[dict]:
    """Per-check_version rollup — the §12.5 ratchet promotion input."""
    q = db.query(
        DoneGateRun.check_version,
        sa_func.count(DoneGateRun.id).label("total"),
        sa_func.count(DoneGateRun.id).filter(DoneGateRun.verdict == "pass").label("passes"),
        sa_func.count(DoneGateRun.id).filter(DoneGateRun.verdict == "fail").label("fails"),
        sa_func.count(DoneGateRun.id).filter(
            DoneGateRun.adjudication.isnot(None)).label("adjudicated"),
        sa_func.count(DoneGateRun.id).filter(
            DoneGateRun.adjudication == "true_positive").label("true_positives"),
        sa_func.count(DoneGateRun.id).filter(
            DoneGateRun.adjudication == "false_positive").label("false_positives"),
        sa_func.count(DoneGateRun.id).filter(
            DoneGateRun.adjudication == "false_negative").label("false_negatives"),
        sa_func.count(DoneGateRun.id).filter(
            DoneGateRun.sampled.is_(True)).label("sampled_total"),
    )
    if project:
        q = q.filter(DoneGateRun.project == project)
    rows = q.group_by(DoneGateRun.check_version).order_by(DoneGateRun.check_version).all()

    result = []
    for r in rows:
        tp, fp = r.true_positives or 0, r.false_positives or 0
        result.append({
            "check_version": r.check_version,
            "total": r.total or 0,
            "passes": r.passes or 0,
            "fails": r.fails or 0,
            "adjudicated": r.adjudicated or 0,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": r.false_negatives or 0,
            "sampled_total": r.sampled_total or 0,
            "precision": (tp / (tp + fp)) if (tp + fp) > 0 else None,
        })
    return result


def adjudicate_run(db: Session, item_id, adjudication: str) -> DoneGateRun | None:
    row = db.query(DoneGateRun).filter(DoneGateRun.id == item_id).first()
    if not row:
        return None
    row.adjudication = adjudication
    db.commit()
    db.refresh(row)
    return row
