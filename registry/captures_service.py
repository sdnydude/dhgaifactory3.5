"""Captures lookup service — natural-key landing verification across capture tables."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from corrections_service import compute_upsert_hash
from models import (
    BugFix,
    Correction,
    DecisionLog,
    DeferredItem,
    Insight,
    SessionReport,
    ShipSession,
    TestCoverage,
)

# pipeline → (Model, natural-key column name). The keys mirror what each
# table's upsert service filters on (and the DB unique constraints enforce).
# corrections handled specially: its natural key is md5(user_message) in
# upsert_key_hash (the DB constraint also includes category; any landed row
# for the same message means the capture landed, which is all landing-diff
# needs). ship_sessions: DB index truncates feature to 255 chars; lookup uses
# full-string equality, mirroring upsert_ship_session's own filter.
PIPELINES = {
    "insights": (Insight, "tldr"),
    "bug_fixes": (BugFix, "tldr"),
    "decision_logs": (DecisionLog, "title"),
    "deferred_items": (DeferredItem, "title"),
    "ship_sessions": (ShipSession, "feature"),
    "test_coverage": (TestCoverage, "title"),
    "session_reports": (SessionReport, "title"),
    "corrections": (Correction, None),
}


def lookup_capture(db: Session, pipeline: str, project: str, key: str) -> Optional[object]:
    """Return the landed row for (pipeline, project, natural key), or None."""
    model, key_col = PIPELINES[pipeline]
    if pipeline == "corrections":
        return db.query(model).filter(
            Correction.project_name == project,
            Correction.upsert_key_hash == compute_upsert_hash(key),
        ).first()
    return db.query(model).filter(
        model.project_name == project,
        getattr(model, key_col) == key,
    ).first()
