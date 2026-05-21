"""Frontend Design Specs service layer — all database operations for frontend_specs."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from models import FrontendDesignSpec

logger = logging.getLogger(__name__)


def list_specs(
    db: Session, *, skip: int = 0, limit: int = 50,
) -> list[FrontendDesignSpec]:
    return db.query(FrontendDesignSpec).offset(skip).limit(limit).all()


def get_spec_by_slug(db: Session, slug: str) -> FrontendDesignSpec | None:
    return db.query(FrontendDesignSpec).filter(FrontendDesignSpec.slug == slug).first()


def create_spec(db: Session, data: dict) -> FrontendDesignSpec:
    """Create a new spec. Raises RuntimeError if slug already exists."""
    existing = db.query(FrontendDesignSpec).filter(FrontendDesignSpec.slug == data["slug"]).first()
    if existing:
        raise RuntimeError(f"Spec with slug '{data['slug']}' already exists")
    spec = FrontendDesignSpec(**data)
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


def update_spec(
    db: Session, slug: str, update_data: dict,
) -> FrontendDesignSpec | None:
    """Update an existing spec by slug. Returns None if not found."""
    spec = db.query(FrontendDesignSpec).filter(FrontendDesignSpec.slug == slug).first()
    if not spec:
        return None
    for field, value in update_data.items():
        setattr(spec, field, value)
    db.commit()
    db.refresh(spec)
    return spec
