"""
DHG Security Admin API — RBAC management endpoints.

All endpoints require authentication via Cloudflare Access JWT.
Admin-only endpoints require the 'admin' role.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from database import get_db
from models import (
    SecurityUser,
    SecurityRole,
    SecurityUserRole,
    SecurityProjectAccess,
    SecurityAuditLog,
)
from auth import (
    AuthenticatedUser,
    get_current_user,
    require_permission,
    require_role,
    get_user_project_ids,
    write_audit_log,
    ROLE_DEFINITIONS,
)
from security_schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    RoleResponse,
    RoleListResponse,
    RoleAssignment,
    RoleRemoval,
    ProjectAccessGrant,
    ProjectAccessResponse,
    ProjectAccessListResponse,
    AuditLogEntry,
    AuditLogListResponse,
    AuthInfoResponse,
)

logger = logging.getLogger("dhg.security.endpoints")

router = APIRouter(prefix="/api/v1/security", tags=["security"])


# =============================================================================
# HELPERS
# =============================================================================

def _user_to_response(user: SecurityUser) -> UserResponse:
    """Convert a SecurityUser ORM object to a UserResponse schema."""
    roles = [ur.role.name for ur in user.user_roles]
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=roles,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _resolve_role(db: Session, role_name: str) -> SecurityRole:
    """Look up a role by name or raise 404."""
    role = db.query(SecurityRole).filter(SecurityRole.name == role_name).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found",
        )
    return role


# =============================================================================
# AUTH INFO
# =============================================================================

@router.get("/auth/me", response_model=AuthInfoResponse)
async def get_auth_info(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's identity, roles, permissions, and accessible project IDs."""
    project_ids = get_user_project_ids(db, user)
    return AuthInfoResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        roles=user.roles,
        permissions=user.permissions,
        project_ids=project_ids,
    )


# =============================================================================
# USER MANAGEMENT (admin only)
# =============================================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_active: Optional[bool] = None,
    admin: AuthenticatedUser = Depends(require_permission("users.read")),
    db: Session = Depends(get_db),
):
    """List all registered users. Requires users.read permission."""
    query = db.query(SecurityUser)
    if is_active is not None:
        query = query.filter(SecurityUser.is_active == is_active)

    total = query.count()
    users = query.order_by(SecurityUser.email).offset(skip).limit(limit).all()
    return UserListResponse(
        users=[_user_to_response(u) for u in users],
        total=total,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    request: Request,
    admin: AuthenticatedUser = Depends(require_permission("users.write")),
    db: Session = Depends(get_db),
):
    """Create a new user and optionally assign roles. Requires users.write permission."""
    existing = db.query(SecurityUser).filter(SecurityUser.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{body.email}' already exists",
        )

    user = SecurityUser(
        email=body.email,
        display_name=body.display_name,
        is_active=body.is_active,
    )
    db.add(user)
    db.flush()  # get user.id before assigning roles

    # Assign requested roles
    for role_name in body.role_names:
        role = _resolve_role(db, role_name)
        db.add(SecurityUserRole(user_id=user.id, role_id=role.id, granted_by=admin.id))

    db.commit()
    db.refresh(user)

    write_audit_log(
        db, admin.email, "user_created",
        user_id=admin.id,
        resource_type="user",
        resource_id=str(user.id),
        detail={"email": body.email, "roles": body.role_names},
        request=request,
    )

    return _user_to_response(user)


@router.get("/users/me")
async def get_current_user_profile(
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Return the authenticated user's profile and roles."""
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "roles": user.roles,
        "permissions": user.permissions,
    }


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin: AuthenticatedUser = Depends(require_permission("users.read")),
    db: Session = Depends(get_db),
):
    """Get a specific user by ID. Requires users.read permission."""
    user = db.query(SecurityUser).filter(SecurityUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_to_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    request: Request,
    admin: AuthenticatedUser = Depends(require_permission("users.write")),
    db: Session = Depends(get_db),
):
    """Update user display name or active status. Requires users.write permission."""
    user = db.query(SecurityUser).filter(SecurityUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    changes = {}
    if body.display_name is not None:
        changes["display_name"] = body.display_name
        user.display_name = body.display_name
    if body.is_active is not None:
        changes["is_active"] = body.is_active
        user.is_active = body.is_active

    db.commit()
    db.refresh(user)

    write_audit_log(
        db, admin.email, "user_updated",
        user_id=admin.id,
        resource_type="user",
        resource_id=str(user_id),
        detail=changes,
        request=request,
    )

    return _user_to_response(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    request: Request,
    admin: AuthenticatedUser = Depends(require_permission("users.delete")),
    db: Session = Depends(get_db),
):
    """Deactivate a user (soft delete). Requires users.delete permission."""
    user = db.query(SecurityUser).filter(SecurityUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user.is_active = False
    db.commit()

    write_audit_log(
        db, admin.email, "user_deactivated",
        user_id=admin.id,
        resource_type="user",
        resource_id=str(user_id),
        detail={"email": user.email},
        request=request,
    )


# =============================================================================
# ROLE MANAGEMENT
# =============================================================================

@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all available roles. Any authenticated user can view roles."""
    roles = db.query(SecurityRole).order_by(SecurityRole.name).all()
    return RoleListResponse(
        roles=[
            RoleResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                permissions=r.permissions or {},
                created_at=r.created_at,
            )
            for r in roles
        ],
        total=len(roles),
    )


@router.post("/users/{user_id}/roles", response_model=UserResponse)
async def assign_role(
    user_id: UUID,
    body: RoleAssignment,
    request: Request,
    admin: AuthenticatedUser = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """Assign a role to a user. Requires roles.write permission."""
    user = db.query(SecurityUser).filter(SecurityUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = _resolve_role(db, body.role_name)

    existing = (
        db.query(SecurityUserRole)
        .filter(SecurityUserRole.user_id == user_id, SecurityUserRole.role_id == role.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already has role '{body.role_name}'",
        )

    db.add(SecurityUserRole(user_id=user_id, role_id=role.id, granted_by=admin.id))
    db.commit()
    db.refresh(user)

    write_audit_log(
        db, admin.email, "role_assigned",
        user_id=admin.id,
        resource_type="user_role",
        resource_id=str(user_id),
        detail={"role": body.role_name},
        request=request,
    )

    return _user_to_response(user)


@router.delete("/users/{user_id}/roles/{role_name}", response_model=UserResponse)
async def remove_role(
    user_id: UUID,
    role_name: str,
    request: Request,
    admin: AuthenticatedUser = Depends(require_permission("roles.write")),
    db: Session = Depends(get_db),
):
    """Remove a role from a user. Requires roles.write permission."""
    user = db.query(SecurityUser).filter(SecurityUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = _resolve_role(db, role_name)

    assignment = (
        db.query(SecurityUserRole)
        .filter(SecurityUserRole.user_id == user_id, SecurityUserRole.role_id == role.id)
        .first()
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User does not have role '{role_name}'",
        )

    db.delete(assignment)
    db.commit()
    db.refresh(user)

    write_audit_log(
        db, admin.email, "role_removed",
        user_id=admin.id,
        resource_type="user_role",
        resource_id=str(user_id),
        detail={"role": role_name},
        request=request,
    )

    return _user_to_response(user)


# =============================================================================
# PROJECT ACCESS
# =============================================================================

@router.get("/users/{user_id}/projects", response_model=ProjectAccessListResponse)
async def list_user_project_access(
    user_id: UUID,
    admin: AuthenticatedUser = Depends(require_permission("users.read")),
    db: Session = Depends(get_db),
):
    """List all project access grants for a user. Requires users.read permission."""
    grants = (
        db.query(SecurityProjectAccess)
        .filter(SecurityProjectAccess.user_id == user_id)
        .order_by(SecurityProjectAccess.granted_at.desc())
        .all()
    )
    return ProjectAccessListResponse(
        grants=[
            ProjectAccessResponse(
                id=g.id,
                user_id=g.user_id,
                project_id=g.project_id,
                access_level=g.access_level,
                granted_by=g.granted_by,
                granted_at=g.granted_at,
            )
            for g in grants
        ],
        total=len(grants),
    )


@router.post("/users/{user_id}/projects", response_model=ProjectAccessResponse, status_code=status.HTTP_201_CREATED)
async def grant_project_access(
    user_id: UUID,
    body: ProjectAccessGrant,
    request: Request,
    admin: AuthenticatedUser = Depends(require_permission("users.write")),
    db: Session = Depends(get_db),
):
    """Grant a user access to a project. Requires users.write permission."""
    user = db.query(SecurityUser).filter(SecurityUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.access_level not in ("viewer", "editor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="access_level must be one of: viewer, editor, admin",
        )

    existing = (
        db.query(SecurityProjectAccess)
        .filter(
            SecurityProjectAccess.user_id == user_id,
            SecurityProjectAccess.project_id == body.project_id,
        )
        .first()
    )
    if existing:
        existing.access_level = body.access_level
        existing.granted_by = admin.id
        db.commit()
        db.refresh(existing)
        grant = existing
    else:
        grant = SecurityProjectAccess(
            user_id=user_id,
            project_id=body.project_id,
            access_level=body.access_level,
            granted_by=admin.id,
        )
        db.add(grant)
        db.commit()
        db.refresh(grant)

    write_audit_log(
        db, admin.email, "project_access_granted",
        user_id=admin.id,
        resource_type="project_access",
        resource_id=str(body.project_id),
        detail={"target_user_id": str(user_id), "access_level": body.access_level},
        request=request,
    )

    return ProjectAccessResponse(
        id=grant.id,
        user_id=grant.user_id,
        project_id=grant.project_id,
        access_level=grant.access_level,
        granted_by=grant.granted_by,
        granted_at=grant.granted_at,
    )


@router.delete("/users/{user_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_project_access(
    user_id: UUID,
    project_id: UUID,
    request: Request,
    admin: AuthenticatedUser = Depends(require_permission("users.write")),
    db: Session = Depends(get_db),
):
    """Revoke a user's access to a project. Requires users.write permission."""
    grant = (
        db.query(SecurityProjectAccess)
        .filter(
            SecurityProjectAccess.user_id == user_id,
            SecurityProjectAccess.project_id == project_id,
        )
        .first()
    )
    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project access grant not found",
        )

    db.delete(grant)
    db.commit()

    write_audit_log(
        db, admin.email, "project_access_revoked",
        user_id=admin.id,
        resource_type="project_access",
        resource_id=str(project_id),
        detail={"target_user_id": str(user_id)},
        request=request,
    )


# =============================================================================
# AUDIT LOG
# =============================================================================

@router.get("/audit", response_model=AuditLogListResponse)
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    action: Optional[str] = None,
    user_email: Optional[str] = None,
    admin: AuthenticatedUser = Depends(require_permission("audit.read")),
    db: Session = Depends(get_db),
):
    """Query the immutable audit log. Requires audit.read permission."""
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

    return AuditLogListResponse(
        entries=[
            AuditLogEntry(
                id=e.id,
                user_id=e.user_id,
                user_email=e.user_email,
                action=e.action,
                resource_type=e.resource_type,
                resource_id=e.resource_id,
                detail=e.detail,
                ip_address=e.ip_address,
                created_at=e.created_at,
            )
            for e in entries
        ],
        total=total,
    )


# =============================================================================
# ROLE SEEDING (called on startup)
# =============================================================================

def seed_roles(db: Session) -> None:
    """Ensure all defined roles exist in the database with current permissions."""
    for role_name, definition in ROLE_DEFINITIONS.items():
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
    logger.info("Security roles seeded: %s", list(ROLE_DEFINITIONS.keys()))
