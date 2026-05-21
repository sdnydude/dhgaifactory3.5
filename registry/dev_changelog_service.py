"""Dev changelog service — DB operations for changelog entries."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models import DevChangelog


def list_dev_changelog(
    db: Session,
    *,
    status: str | None = None,
    category: str | None = None,
    window_start: date | None = None,
    window_end: date | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[DevChangelog], int]:
    """Return (rows, total) with optional filters."""
    query = db.query(DevChangelog)

    if status:
        display_status = func.coalesce(DevChangelog.declared_status, DevChangelog.detected_status)
        query = query.filter(display_status == status)
    if category:
        query = query.filter(DevChangelog.category == category)
    if window_start:
        query = query.filter(DevChangelog.window_start >= window_start)
    if window_end:
        query = query.filter(DevChangelog.window_start <= window_end)
    if q:
        needle = f"%{q}%"
        query = query.filter(
            or_(
                DevChangelog.epic.ilike(needle),
                DevChangelog.key_insight.ilike(needle),
                DevChangelog.notes.ilike(needle),
            )
        )

    total = query.count()
    rows = (
        query.order_by(DevChangelog.window_start.desc(), DevChangelog.slug.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def get_by_slug(db: Session, slug: str) -> DevChangelog | None:
    return db.query(DevChangelog).filter(DevChangelog.slug == slug).first()


def patch_by_slug(
    db: Session, slug: str, updates: dict,
) -> DevChangelog | None:
    """Apply human-owned field updates. Returns None if not found."""
    row = db.query(DevChangelog).filter(DevChangelog.slug == slug).first()
    if not row:
        return None

    for field, value in updates.items():
        setattr(row, field, value)

    now = datetime.now(timezone.utc)
    row.last_human_edit_at = now
    row.updated_at = now

    db.commit()
    db.refresh(row)
    return row
