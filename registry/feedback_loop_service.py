"""Feedback Loop service — unified health check across all 7 memreg capture types."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from models import (
    BugFix,
    Correction,
    DecisionLog,
    DeferredItem,
    Insight,
    ShipSession,
    TestCoverage,
)

logger = logging.getLogger(__name__)

MEMREG_TYPES = [
    ("corrections", Correction),
    ("bug_fixes", BugFix),
    ("insights", Insight),
    ("decision_logs", DecisionLog),
    ("deferred_items", DeferredItem),
    ("test_coverage", TestCoverage),
    ("ship_sessions", ShipSession),
]


def feedback_loop_health(
    db: Session,
    *,
    project_name: str | None = None,
) -> dict:
    cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)

    type_stats = []
    healthy_count = 0

    for type_name, model in MEMREG_TYPES:
        q = db.query(
            sa_func.count(model.id).label("total"),
            sa_func.count(model.id).filter(model.created_at >= cutoff_7d).label("count_7d"),
            sa_func.max(model.created_at).label("last_ever"),
        )
        if project_name:
            q = q.filter(model.project_name == project_name)

        row = q.one()
        total = row.total or 0
        count_7d = row.count_7d or 0
        last_capture = row.last_ever

        if count_7d > 0:
            healthy_count += 1

        type_stats.append({
            "type": type_name,
            "count_7d": count_7d,
            "count_total": total,
            "last_capture": last_capture.isoformat() if last_capture else None,
        })

    total_types = len(MEMREG_TYPES)
    if healthy_count == total_types:
        status = "healthy"
    elif healthy_count == 0:
        status = "dead"
    else:
        status = "degraded"

    return {
        "status": status,
        "healthy_types": healthy_count,
        "total_types": total_types,
        "types": type_stats,
    }
