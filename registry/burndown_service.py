"""Burndown Lists service layer — all database operations for burndown_lists and burndown_items."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session, joinedload

from models import BurndownList, BurndownItem
from burndown_schemas import (
    BurndownListCreate,
    BurndownListUpdate,
    BurndownItemCreate,
    BurndownItemUpdate,
)

logger = logging.getLogger(__name__)


def create_list(db: Session, payload: BurndownListCreate) -> BurndownList:
    row = BurndownList(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_list(db: Session, list_id: UUID) -> BurndownList | None:
    return (
        db.query(BurndownList)
        .options(joinedload(BurndownList.items))
        .filter(BurndownList.id == list_id)
        .first()
    )


def list_burndowns(
    db: Session,
    *,
    project_name: str | None = None,
    status: str | None = None,
    list_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[BurndownList], int]:
    q = db.query(BurndownList)
    if project_name:
        q = q.filter(BurndownList.project_name == project_name)
    if status:
        q = q.filter(BurndownList.status == status)
    if list_type:
        q = q.filter(BurndownList.list_type == list_type)

    total = q.count()
    rows = q.order_by(BurndownList.created_at.desc()).offset(offset).limit(limit).all()
    return rows, total


def update_list(db: Session, list_id: UUID, payload: BurndownListUpdate) -> BurndownList | None:
    row = db.query(BurndownList).filter(BurndownList.id == list_id).first()
    if not row:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_list(db: Session, list_id: UUID) -> bool:
    row = db.query(BurndownList).filter(BurndownList.id == list_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# --- Item operations ---

def add_items(db: Session, list_id: UUID, items: list[BurndownItemCreate]) -> list[BurndownItem]:
    bl = db.query(BurndownList).filter(BurndownList.id == list_id).first()
    if not bl:
        return []
    rows = []
    for item in items:
        row = BurndownItem(list_id=list_id, **item.model_dump())
        db.add(row)
        rows.append(row)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows


def update_item(db: Session, item_id: UUID, payload: BurndownItemUpdate) -> BurndownItem | None:
    row = db.query(BurndownItem).filter(BurndownItem.id == item_id).first()
    if not row:
        return None
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] in ("pass", "fail", "blocked"):
        updates["checked_at"] = datetime.now(timezone.utc)
    for field, value in updates.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_item(db: Session, item_id: UUID) -> bool:
    row = db.query(BurndownItem).filter(BurndownItem.id == item_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def get_list_stats(db: Session, list_id: UUID) -> dict:
    items = db.query(BurndownItem).filter(BurndownItem.list_id == list_id).all()
    total = len(items)
    counts = {"not_started": 0, "pass": 0, "fail": 0, "blocked": 0, "skipped": 0}
    for item in items:
        if item.status in counts:
            counts[item.status] += 1
    return {
        "total": total,
        **counts,
        "progress_pct": round((counts["pass"] + counts["skipped"]) / total * 100, 1) if total else 0,
    }
