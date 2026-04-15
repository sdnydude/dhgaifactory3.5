from __future__ import annotations

from contextlib import contextmanager

from registry.database import SessionLocal


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
