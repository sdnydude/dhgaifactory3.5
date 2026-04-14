"""Dev Changelog admin/reporting API endpoints.

Routes:
  GET    /api/dev-changelog         list with filters (status, category, window range, q, limit, offset)
  GET    /api/dev-changelog/{slug}  detail
  PATCH  /api/dev-changelog/{slug}  human-owned fields only (bumps last_human_edit_at + updated_at)

`status` filters on the display status = COALESCE(declared_status, detected_status).
Agent-owned fields cannot be written through this API — DevChangelogPatch enforces
extra='forbid' at the schema layer, rejecting agent-owned keys before the handler runs.
"""
import os
import sys
import time
import logging
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from models import DevChangelog
from dev_changelog_schemas import (
    DevChangelogEntry,
    DevChangelogList,
    DevChangelogPatch,
)

logger = logging.getLogger(__name__)

try:
    from api import (
        registry_read_latency,
        registry_read_operations,
        registry_write_latency,
        registry_write_operations,
        registry_errors,
    )
except ImportError:
    from prometheus_client import Counter, Histogram
    registry_read_latency = Histogram(
        "registry_read_latency", "Read latency",
        buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
    )
    registry_read_operations = Counter(
        "registry_read_operations", "Read operations", ["operation"],
    )
    registry_write_latency = Histogram(
        "registry_write_latency", "Write latency",
        buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
    )
    registry_write_operations = Counter(
        "registry_write_operations", "Write operations", ["operation"],
    )
    registry_errors = Counter(
        "registry_errors", "Registry errors", ["error_type"],
    )


router = APIRouter(prefix="/api/dev-changelog", tags=["dev-changelog"])


@router.get("", response_model=DevChangelogList)
async def list_dev_changelog(
    status: Optional[str] = Query(None, description="Filter by display status (COALESCE(declared, detected))"),
    category: Optional[str] = Query(None),
    window_start: Optional[date] = Query(None, description="Inclusive lower bound on window_start"),
    window_end: Optional[date] = Query(None, description="Inclusive upper bound on window_start"),
    q: Optional[str] = Query(None, description="Text search on epic + key_insight + notes"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> DevChangelogList:
    start = time.time()
    try:
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

        registry_read_operations.labels(operation="list_dev_changelog").inc()
        registry_read_latency.observe((time.time() - start) * 1000)

        return DevChangelogList(
            entries=[DevChangelogEntry.model_validate(r) for r in rows],
            total=total,
        )
    except Exception as e:
        registry_errors.labels(error_type="list_dev_changelog").inc()
        logger.exception("list_dev_changelog failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}", response_model=DevChangelogEntry)
async def get_dev_changelog(slug: str, db: Session = Depends(get_db)) -> DevChangelogEntry:
    start = time.time()
    try:
        row = db.query(DevChangelog).filter(DevChangelog.slug == slug).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"dev_changelog entry '{slug}' not found")

        registry_read_operations.labels(operation="get_dev_changelog").inc()
        registry_read_latency.observe((time.time() - start) * 1000)

        return DevChangelogEntry.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        registry_errors.labels(error_type="get_dev_changelog").inc()
        logger.exception("get_dev_changelog failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{slug}", response_model=DevChangelogEntry)
async def patch_dev_changelog(
    slug: str,
    patch: DevChangelogPatch,
    db: Session = Depends(get_db),
) -> DevChangelogEntry:
    start = time.time()
    try:
        row = db.query(DevChangelog).filter(DevChangelog.slug == slug).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"dev_changelog entry '{slug}' not found")

        updates = patch.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="PATCH body must include at least one human-owned field")

        for field, value in updates.items():
            setattr(row, field, value)

        now = datetime.now(timezone.utc)
        row.last_human_edit_at = now
        row.updated_at = now

        db.commit()
        db.refresh(row)

        registry_write_operations.labels(operation="patch_dev_changelog").inc()
        registry_write_latency.observe((time.time() - start) * 1000)

        return DevChangelogEntry.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="patch_dev_changelog").inc()
        logger.exception("patch_dev_changelog failed")
        raise HTTPException(status_code=500, detail=str(e))
