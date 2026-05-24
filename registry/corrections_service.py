"""Corrections service layer — all database operations for corrections."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Correction
from corrections_schemas import CorrectionCreate

logger = logging.getLogger(__name__)


def compute_upsert_hash(user_message: str) -> str:
    return hashlib.md5(user_message.encode("utf-8")).hexdigest()


def upsert_correction(
    db: Session, payload: CorrectionCreate, upsert_hash: str, embedding=None,
) -> tuple[Correction, bool]:
    """Upsert by (project_name, category, upsert_key_hash). Returns (row, created)."""
    existing = db.query(Correction).filter(
        Correction.project_name == payload.project_name,
        Correction.category == payload.category,
        Correction.upsert_key_hash == upsert_hash,
    ).first()

    if existing:
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = Correction(**payload.model_dump())
    row.upsert_key_hash = upsert_hash
    if embedding:
        row.embedding = embedding
        row.embedding_model = "nomic-embed-text"
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(Correction).filter(
            Correction.project_name == payload.project_name,
            Correction.category == payload.category,
            Correction.upsert_key_hash == upsert_hash,
        ).first()
        if not existing:
            raise RuntimeError("Conflict: row vanished between insert and re-query")
        _apply_fields(existing, payload, embedding)
        db.commit()
        db.refresh(existing)
        return existing, False

    db.commit()
    db.refresh(row)
    return row, True


def list_corrections(
    db: Session,
    *,
    project_name: str | None = None,
    category: str | None = None,
    since_days: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Correction], int]:
    q = db.query(Correction)
    if project_name:
        q = q.filter(Correction.project_name == project_name)
    if category:
        q = q.filter(Correction.category == category)
    if since_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        q = q.filter(Correction.created_at >= cutoff)

    total = q.count()
    rows = q.order_by(Correction.created_at.desc()).offset(offset).limit(limit).all()
    return rows, total


def search_corrections(
    db: Session,
    query_text: str,
    *,
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> tuple[list[Correction], int]:
    ts_query = sa_func.plainto_tsquery("english", query_text)
    q = db.query(Correction).filter(Correction.search_vector.op("@@")(ts_query))
    if project_name:
        q = q.filter(Correction.project_name == project_name)
    if category:
        q = q.filter(Correction.category == category)

    total = q.count()
    rows = (
        q.order_by(sa_func.ts_rank(Correction.search_vector, ts_query).desc())
        .limit(limit)
        .all()
    )
    return rows, total


def correction_stats(
    db: Session,
    *,
    project_name: str | None = None,
    since_days: int = 7,
) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    q = db.query(
        Correction.category,
        sa_func.count(Correction.id).label("count"),
    ).filter(Correction.created_at >= cutoff)
    if project_name:
        q = q.filter(Correction.project_name == project_name)

    rows = q.group_by(Correction.category).order_by(sa_func.count(Correction.id).desc()).all()
    return [{"category": r.category, "count": r.count} for r in rows]


def correction_stats_enhanced(
    db: Session,
    *,
    project_name: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    cutoff_prev_7d = now - timedelta(days=14)

    filters = []
    if project_name:
        filters.append(Correction.project_name == project_name)

    q = db.query(
        Correction.category,
        sa_func.count(Correction.id).label("count_all"),
        sa_func.count(Correction.id).filter(Correction.created_at >= cutoff_7d).label("count_7d"),
        sa_func.count(Correction.id).filter(Correction.created_at >= cutoff_30d).label("count_30d"),
        sa_func.count(Correction.id).filter(
            Correction.created_at >= cutoff_prev_7d,
            Correction.created_at < cutoff_7d,
        ).label("prev_7d"),
        sa_func.max(Correction.created_at).label("most_recent"),
    )
    for f in filters:
        q = q.filter(f)
    rows = q.group_by(Correction.category).all()

    most_recent_msgs: dict[str, str] = {}
    if rows:
        cats_with_data = [r.category for r in rows if r.most_recent is not None]
        if cats_with_data:
            from sqlalchemy import tuple_
            sub = db.query(
                Correction.category,
                sa_func.substring(Correction.user_message, 1, 200).label("msg"),
            ).filter(
                tuple_(Correction.category, Correction.created_at).in_(
                    db.query(Correction.category, sa_func.max(Correction.created_at))
                    .filter(Correction.category.in_(cats_with_data), *filters)
                    .group_by(Correction.category)
                )
            ).all()
            for s in sub:
                most_recent_msgs[s.category] = s.msg or ""

    result = []
    for r in rows:
        count_7d = r.count_7d or 0
        prev = r.prev_7d or 0
        if count_7d > prev:
            trend = "increasing"
        elif count_7d < prev:
            trend = "decreasing"
        else:
            trend = "stable"

        result.append({
            "category": r.category,
            "count_7d": count_7d,
            "count_30d": r.count_30d or 0,
            "count_all": r.count_all or 0,
            "most_recent": r.most_recent,
            "most_recent_message": most_recent_msgs.get(r.category),
            "repeat_flag": count_7d > 2,
            "trend": trend,
        })

    result.sort(key=lambda x: x["count_7d"], reverse=True)

    total_7d = sum(e["count_7d"] for e in result)
    total_30d = sum(e["count_30d"] for e in result)
    total_all = sum(e["count_all"] for e in result)
    active_repeats = [e["category"] for e in result if e["repeat_flag"]]
    top = result[0] if result else None

    return {
        "total_7d": total_7d,
        "total_30d": total_30d,
        "total_all": total_all,
        "categories": result,
        "active_repeats": active_repeats,
        "top_pattern": top["category"] if top and top["count_7d"] > 0 else None,
        "top_pattern_count": top["count_7d"] if top else None,
        "top_pattern_example": top["most_recent_message"] if top and top["count_7d"] > 0 else None,
    }


def delete_correction(db: Session, item_id: UUID) -> Correction | None:
    row = db.query(Correction).filter(Correction.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


def _apply_fields(existing: Correction, payload: CorrectionCreate, embedding) -> None:
    existing.user_message = payload.user_message
    existing.context = payload.context
    existing.claude_action = payload.claude_action
    existing.session_id = payload.session_id
    existing.tags = payload.tags
    existing.model_name = payload.model_name
    existing.meta_data = payload.meta_data
    if embedding:
        existing.embedding = embedding
        existing.embedding_model = "nomic-embed-text"
