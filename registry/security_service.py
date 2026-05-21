"""Security service layer — all database operations for RBAC management."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from models import (
    SecurityUser,
    SecurityRole,
    SecurityUserRole,
    SecurityProjectAccess,
    SecurityAuditLog,
)

logger = logging.getLogger(__name__)


def list_users(
    db: Session,
    *,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[SecurityUser], int]:
    query = db.query(SecurityUser)
    if is_active is not None:
        query = query.filter(SecurityUser.is_active == is_active)
    total = query.count()
    users = query.order_by(SecurityUser.email).offset(skip).limit(limit).all()
    return users, total


def get_user(db: Session, user_id: UUID) -> SecurityUser | None:
    return db.query(SecurityUser).filter(SecurityUser.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> SecurityUser | None:
    return db.query(SecurityUser).filter(SecurityUser.email == email).first()


def create_user(
    db: Session, email: str, display_name: str, is_active: bool,
    role_names: list[str], granted_by: UUID,
) -> SecurityUser:
    """Create a user and assign roles. Raises RuntimeError if email exists."""
    existing = db.query(SecurityUser).filter(SecurityUser.email == email).first()
    if existing:
        raise RuntimeError(f"User with email '{email}' already exists")

    user = SecurityUser(email=email, display_name=display_name, is_active=is_active)
    db.add(user)
    db.flush()

    for role_name in role_names:
        role = resolve_role(db, role_name)
        if not role:
            raise RuntimeError(f"Role '{role_name}' not found")
        db.add(SecurityUserRole(user_id=user.id, role_id=role.id, granted_by=granted_by))

    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session, user_id: UUID, changes: dict,
) -> SecurityUser | None:
    user = db.query(SecurityUser).filter(SecurityUser.id == user_id).first()
    if not user:
        return None
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: UUID) -> SecurityUser | None:
    user = db.query(SecurityUser).filter(SecurityUser.id == user_id).first()
    if not user:
        return None
    user.is_active = False
    db.commit()
    return user


def list_roles(db: Session) -> list[SecurityRole]:
    return db.query(SecurityRole).order_by(SecurityRole.name).all()


def resolve_role(db: Session, role_name: str) -> SecurityRole | None:
    return db.query(SecurityRole).filter(SecurityRole.name == role_name).first()


def assign_role(
    db: Session, user_id: UUID, role_id: UUID, granted_by: UUID,
) -> SecurityUserRole | None:
    """Assign a role. Returns None if user not found. Raises RuntimeError if already assigned."""
    user = db.query(SecurityUser).filter(SecurityUser.id == user_id).first()
    if not user:
        return None

    existing = (
        db.query(SecurityUserRole)
        .filter(SecurityUserRole.user_id == user_id, SecurityUserRole.role_id == role_id)
        .first()
    )
    if existing:
        raise RuntimeError("already_assigned")

    assignment = SecurityUserRole(user_id=user_id, role_id=role_id, granted_by=granted_by)
    db.add(assignment)
    db.commit()
    db.refresh(user)
    return assignment


def remove_role(
    db: Session, user_id: UUID, role_id: UUID,
) -> bool:
    """Remove a role assignment. Returns False if not found."""
    assignment = (
        db.query(SecurityUserRole)
        .filter(SecurityUserRole.user_id == user_id, SecurityUserRole.role_id == role_id)
        .first()
    )
    if not assignment:
        return False
    db.delete(assignment)
    db.commit()
    return True


def list_user_project_access(
    db: Session, user_id: UUID,
) -> list[SecurityProjectAccess]:
    return (
        db.query(SecurityProjectAccess)
        .filter(SecurityProjectAccess.user_id == user_id)
        .order_by(SecurityProjectAccess.granted_at.desc())
        .all()
    )


def grant_project_access(
    db: Session, user_id: UUID, project_id: UUID,
    access_level: str, granted_by: UUID,
) -> SecurityProjectAccess:
    """Upsert project access. Returns the grant (new or updated)."""
    existing = (
        db.query(SecurityProjectAccess)
        .filter(
            SecurityProjectAccess.user_id == user_id,
            SecurityProjectAccess.project_id == project_id,
        )
        .first()
    )
    if existing:
        existing.access_level = access_level
        existing.granted_by = granted_by
        db.commit()
        db.refresh(existing)
        return existing

    grant = SecurityProjectAccess(
        user_id=user_id,
        project_id=project_id,
        access_level=access_level,
        granted_by=granted_by,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


def revoke_project_access(
    db: Session, user_id: UUID, project_id: UUID,
) -> bool:
    """Revoke project access. Returns False if not found."""
    grant = (
        db.query(SecurityProjectAccess)
        .filter(
            SecurityProjectAccess.user_id == user_id,
            SecurityProjectAccess.project_id == project_id,
        )
        .first()
    )
    if not grant:
        return False
    db.delete(grant)
    db.commit()
    return True


def list_audit_logs(
    db: Session,
    *,
    action: str | None = None,
    user_email: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[SecurityAuditLog], int]:
    query = db.query(SecurityAuditLog)
    if action:
        query = query.filter(SecurityAuditLog.action == action)
    if user_email:
        query = query.filter(SecurityAuditLog.user_email == user_email)

    total = query.count()
    entries = (
        query.order_by(SecurityAuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries, total


def seed_roles(db: Session, role_definitions: dict) -> None:
    """Ensure all defined roles exist in the database with current permissions."""
    for role_name, definition in role_definitions.items():
        existing = db.query(SecurityRole).filter(SecurityRole.name == role_name).first()
        if existing:
            existing.description = definition["description"]
            existing.permissions = definition["permissions"]
        else:
            db.add(SecurityRole(
                name=role_name,
                description=definition["description"],
                permissions=definition["permissions"],
            ))
    db.commit()
    logger.info("Security roles seeded: %s", list(role_definitions.keys()))
