"""Assets service layer — all database operations for the assets table."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Asset
from assets_schemas import AssetCreate

logger = logging.getLogger(__name__)

_UPDATE_FIELDS = (
    "filename", "filepath", "source_path", "source_drive", "design_system",
    "category", "mime_type", "file_size_bytes", "width", "height",
    "dominant_color", "alt_text", "exif", "tags", "model_name", "meta_data",
)


def upsert_asset(db: Session, payload: AssetCreate) -> tuple[Asset, bool]:
    """Upsert by (project_name, sha256). Returns (row, created)."""
    existing = db.query(Asset).filter(
        Asset.project_name == payload.project_name,
        Asset.sha256 == payload.sha256,
    ).first()
    if existing:
        for f in _UPDATE_FIELDS:
            setattr(existing, f, getattr(payload, f))
        db.commit()
        db.refresh(existing)
        return existing, False

    row = Asset(**payload.model_dump())
    try:
        db.add(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(Asset).filter(
            Asset.project_name == payload.project_name,
            Asset.sha256 == payload.sha256,
        ).first()
        if not existing:
            raise RuntimeError("Conflict: row vanished between insert and re-query")
        for f in _UPDATE_FIELDS:
            setattr(existing, f, getattr(payload, f))
        db.commit()
        db.refresh(existing)
        return existing, False

    db.commit()
    db.refresh(row)
    return row, True


def bulk_upsert(db: Session, project_name: str, assets: list[AssetCreate]) -> tuple[int, int]:
    """Upsert a batch. Returns (created, updated)."""
    created = updated = 0
    for a in assets:
        data = a.model_copy(update={"project_name": project_name})
        _, was_created = upsert_asset(db, data)
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated


def list_assets(
    db: Session, *,
    project_name: str | None = None,
    category: str | None = None,
    source_drive: str | None = None,
    design_system: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[Asset], int]:
    q = db.query(Asset)
    if project_name:
        q = q.filter(Asset.project_name == project_name)
    if category:
        q = q.filter(Asset.category == category)
    if source_drive:
        q = q.filter(Asset.source_drive == source_drive)
    if design_system:
        q = q.filter(Asset.design_system == design_system)
    total = q.count()
    rows = q.order_by(Asset.created_at.desc()).offset(offset).limit(limit).all()
    return rows, total


def search_assets(
    db: Session, query_text: str, *,
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> tuple[list[Asset], int]:
    tsq = sa_func.plainto_tsquery("english", query_text)
    q = db.query(Asset).filter(Asset.search_vector.op("@@")(tsq))
    if project_name:
        q = q.filter(Asset.project_name == project_name)
    if category:
        q = q.filter(Asset.category == category)
    total = q.count()
    rows = q.order_by(sa_func.ts_rank(Asset.search_vector, tsq).desc()).limit(limit).all()
    return rows, total


def get_asset(db: Session, item_id: UUID) -> Asset | None:
    return db.query(Asset).filter(Asset.id == item_id).first()


def delete_asset(db: Session, item_id: UUID) -> Asset | None:
    row = db.query(Asset).filter(Asset.id == item_id).first()
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row
