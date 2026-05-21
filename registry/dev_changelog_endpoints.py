"""Dev Changelog admin/reporting API endpoints.

Routes:
  GET    /api/dev-changelog         list with filters (status, category, window range, q, limit, offset)
  GET    /api/dev-changelog/{slug}  detail
  PATCH  /api/dev-changelog/{slug}  human-owned fields only (bumps last_human_edit_at + updated_at)

`status` filters on the display status = COALESCE(declared_status, detected_status).
Agent-owned fields cannot be written through this API — DevChangelogPatch enforces
extra='forbid' at the schema layer, rejecting agent-owned keys before the handler runs.
"""
import time
import logging
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
import dev_changelog_service as svc
from dev_changelog_schemas import (
    DevChangelogEntry,
    DevChangelogList,
    DevChangelogPatch,
)

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_write_latency,
    registry_write_operations,
    registry_errors,
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
        rows, total = svc.list_dev_changelog(
            db, status=status, category=category,
            window_start=window_start, window_end=window_end,
            q=q, limit=limit, offset=offset,
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
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{slug}", response_model=DevChangelogEntry)
async def get_dev_changelog(slug: str, db: Session = Depends(get_db)) -> DevChangelogEntry:
    start = time.time()
    try:
        row = svc.get_by_slug(db, slug)
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
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{slug}", response_model=DevChangelogEntry)
async def patch_dev_changelog(
    slug: str,
    patch: DevChangelogPatch,
    db: Session = Depends(get_db),
) -> DevChangelogEntry:
    start = time.time()
    try:
        updates = patch.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="PATCH body must include at least one human-owned field")

        row = svc.patch_by_slug(db, slug, updates)
        if not row:
            raise HTTPException(status_code=404, detail=f"dev_changelog entry '{slug}' not found")

        registry_write_operations.labels(operation="patch_dev_changelog").inc()
        registry_write_latency.observe((time.time() - start) * 1000)

        return DevChangelogEntry.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        registry_errors.labels(error_type="patch_dev_changelog").inc()
        logger.exception("patch_dev_changelog failed")
        raise HTTPException(status_code=500, detail="Internal server error")
