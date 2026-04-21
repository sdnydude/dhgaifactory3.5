"""
DHG Security — Authentication and Authorization

Layer 3 of the defense-in-depth stack:
  Layer 1: Cloudflare Access + WAF (authentication, DDoS, bot protection)
  Layer 2: Next.js Middleware (JWT validation, session, RBAC headers)
  Layer 3: FastAPI Middleware (JWT re-validation, permission enforcement, audit log)  <-- THIS
  Layer 4: PostgreSQL (RBAC tables, row-level project scoping)

Validates Cloudflare Access JWTs, resolves users, enforces role-based permissions,
and logs every security-relevant action to an immutable audit trail.
"""
import os
import time
import logging
from datetime import datetime, timezone
from typing import List, Optional

import jwt
import httpx
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    SecurityUser,
    SecurityProjectAccess,
    SecurityAuditLog,
)

logger = logging.getLogger("dhg.security")

# =============================================================================
# CONFIGURATION
# =============================================================================

CF_TEAM_DOMAIN = os.getenv("CF_ACCESS_TEAM_DOMAIN", "digitalharmonygroup")
CF_ACCESS_AUD = os.getenv("CF_ACCESS_AUD", "")
SECURITY_DEV_MODE = os.getenv("SECURITY_DEV_MODE", "false").lower() == "true"

if SECURITY_DEV_MODE:
    logger.warning(
        "SECURITY_DEV_MODE is enabled — authentication is bypassed. "
        "This MUST be disabled in production."
    )


# =============================================================================
# ROLE DEFINITIONS (seeded into security_roles table)
# =============================================================================

ROLE_DEFINITIONS = {
    "admin": {
        "description": "Full system access — user management, role assignment, all projects, settings",
        "permissions": {
            "users.read": True, "users.write": True, "users.delete": True,
            "roles.read": True, "roles.write": True,
            "projects.read": True, "projects.write": True, "projects.delete": True,
            "reviews.read": True, "reviews.write": True,
            "audit.read": True,
            "settings.read": True, "settings.write": True,
            "all_projects": True,
        },
    },
    "operations": {
        "description": "Project management and team operations",
        "permissions": {
            "users.read": True,
            "projects.read": True, "projects.write": True,
            "reviews.read": True, "reviews.write": True,
            "audit.read": True,
            "all_projects": True,
        },
    },
    "finance": {
        "description": "Financial data access — project costs, reports, budgets",
        "permissions": {
            "projects.read": True,
            "reports.read": True,
            "costs.read": True,
            "all_projects": True,
        },
    },
    "editor": {
        "description": "Content editing on assigned projects with review comments",
        "permissions": {
            "projects.read": True,
            "projects.write": True,
            "reviews.read": True,
            "reviews.write": True,
        },
    },
    "viewer": {
        "description": "Read-only access to assigned projects",
        "permissions": {
            "projects.read": True,
            "reviews.read": True,
        },
    },
}


# =============================================================================
# CLOUDFLARE ACCESS JWT VALIDATION
# =============================================================================

_jwks_cache: dict = {"keys": None, "fetched_at": 0.0}
JWKS_CACHE_TTL = 3600  # seconds


def _get_cf_certs_url() -> str:
    return f"https://{CF_TEAM_DOMAIN}.cloudflareaccess.com/cdn-cgi/access/certs"


def get_cf_jwks(force_refresh: bool = False) -> dict:
    """Fetch and cache Cloudflare Access JWKS public keys."""
    now = time.time()
    if (
        not force_refresh
        and _jwks_cache["keys"]
        and (now - _jwks_cache["fetched_at"]) < JWKS_CACHE_TTL
    ):
        return _jwks_cache["keys"]

    certs_url = _get_cf_certs_url()
    try:
        response = httpx.get(certs_url, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch Cloudflare JWKS from %s: %s", certs_url, exc)
        if _jwks_cache["keys"]:
            logger.warning("Using stale JWKS cache after fetch failure")
            return _jwks_cache["keys"]
        raise ValueError(f"Cannot fetch Cloudflare signing keys: {exc}") from exc

    jwks = response.json()
    _jwks_cache["keys"] = jwks
    _jwks_cache["fetched_at"] = now
    return jwks


def validate_cf_token(token: str) -> dict:
    """Validate a Cloudflare Access JWT and return its claims.

    Raises ValueError on any validation failure.
    """
    if not CF_ACCESS_AUD:
        raise ValueError("CF_ACCESS_AUD environment variable is not configured")

    jwks = get_cf_jwks()

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        raise ValueError("JWT header missing 'kid' field")

    # Find matching key
    public_key = None
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
            break

    # If kid not found, force-refresh JWKS (key rotation may have occurred)
    if not public_key:
        jwks = get_cf_jwks(force_refresh=True)
        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
                break

    if not public_key:
        raise ValueError(f"No matching signing key for kid={kid}")

    issuer = f"https://{CF_TEAM_DOMAIN}.cloudflareaccess.com"
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=CF_ACCESS_AUD,
        issuer=issuer,
    )
    return claims


# =============================================================================
# AUTHENTICATED USER
# =============================================================================

class AuthenticatedUser:
    """Resolved user identity with aggregated roles and permissions."""

    def __init__(self, user: SecurityUser, roles: List[str], permissions: dict):
        self.id = user.id
        self.email = user.email
        self.display_name = user.display_name
        self.is_active = user.is_active
        self.roles = roles
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        return self.permissions.get(permission, False)

    def has_role(self, role_name: str) -> bool:
        return role_name in self.roles

    def has_any_role(self, *role_names: str) -> bool:
        return any(r in self.roles for r in role_names)


# =============================================================================
# AUDIT LOGGING
# =============================================================================

def write_audit_log(
    db: Session,
    user_email: str,
    action: str,
    *,
    user_id=None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail: Optional[dict] = None,
    request: Optional[Request] = None,
):
    """Write an immutable audit log entry."""
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.headers.get("X-Forwarded-For", request.client.host if request.client else None)
        user_agent = request.headers.get("User-Agent")

    entry = SecurityAuditLog(
        user_id=user_id,
        user_email=user_email,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to write audit log entry for action=%s", action)


# =============================================================================
# FASTAPI DEPENDENCIES
# =============================================================================

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """Resolve the authenticated user from the request.

    Priority:
      1. Cf-Access-Jwt-Assertion header (Cloudflare Access JWT)
      2. X-User-Email header (internal Next.js proxy — only when JWT also present or dev mode)
      3. SECURITY_DEV_MODE bypass (development only)
    """
    email: Optional[str] = None
    auth_source = "none"

    # --- Cloudflare JWT ---
    cf_token = request.headers.get("Cf-Access-Jwt-Assertion")
    if cf_token:
        try:
            claims = validate_cf_token(cf_token)
            email = claims.get("email")
            auth_source = "cloudflare_jwt"
        except Exception as exc:
            logger.warning("Cloudflare JWT validation failed: %s", exc)
            write_audit_log(
                db, "unknown", "auth_failed",
                detail={"error": str(exc), "source": "cloudflare_jwt"},
                request=request,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

    # --- Internal proxy header (accepted alongside valid JWT or in dev mode) ---
    if not email:
        internal_email = request.headers.get("X-User-Email")
        if internal_email and SECURITY_DEV_MODE:
            email = internal_email
            auth_source = "dev_header"
            logger.warning("SECURITY_DEV_MODE: accepting X-User-Email=%s", email)

    # --- Dev fallback ---
    if not email and SECURITY_DEV_MODE:
        email = "dev@digitalharmonyai.com"
        auth_source = "dev_fallback"
        logger.warning("SECURITY_DEV_MODE: using fallback dev user")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # --- Resolve user ---
    user = db.query(SecurityUser).filter(SecurityUser.email == email).first()

    if not user:
        write_audit_log(
            db, email, "access_denied_not_registered",
            detail={"auth_source": auth_source},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not registered in the system",
        )

    if not user.is_active:
        write_audit_log(
            db, email, "access_denied_inactive",
            user_id=user.id,
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Aggregate roles and permissions
    roles: List[str] = []
    permissions: dict = {}
    for user_role in user.user_roles:
        role = user_role.role
        roles.append(role.name)
        if role.permissions:
            for perm, value in role.permissions.items():
                if value:
                    permissions[perm] = True

    write_audit_log(
        db, email, "authenticated",
        user_id=user.id,
        detail={"auth_source": auth_source, "roles": roles},
        request=request,
    )

    return AuthenticatedUser(user=user, roles=roles, permissions=permissions)


def require_permission(permission: str):
    """Dependency factory: require the current user to hold a specific permission."""
    async def _check(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> AuthenticatedUser:
        if not user.has_permission(permission):
            write_audit_log(
                db, user.email, "permission_denied",
                user_id=user.id,
                detail={"required": permission, "user_roles": user.roles},
                request=request,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user
    return _check


def require_role(*role_names: str):
    """Dependency factory: require the current user to hold at least one of the listed roles."""
    async def _check(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> AuthenticatedUser:
        if not user.has_any_role(*role_names):
            write_audit_log(
                db, user.email, "role_denied",
                user_id=user.id,
                detail={"required_any": list(role_names), "user_roles": user.roles},
                request=request,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {' or '.join(role_names)}",
            )
        return user
    return _check


def get_user_project_ids(db: Session, user: AuthenticatedUser) -> Optional[List]:
    """Return list of project IDs the user can access, or None if they have all_projects."""
    if user.has_permission("all_projects"):
        return None  # None means "no filter — user sees everything"

    rows = (
        db.query(SecurityProjectAccess.project_id)
        .filter(SecurityProjectAccess.user_id == user.id)
        .all()
    )
    return [row.project_id for row in rows]
