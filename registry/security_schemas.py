"""
Pydantic schemas for the DHG Security / RBAC API.

Covers user management, role assignment, project access grants,
and audit log queries.
"""
from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# USER SCHEMAS
# =============================================================================

class UserCreate(BaseModel):
    email: str = Field(..., max_length=255, description="Email address (must match Cloudflare Access identity)")
    display_name: str = Field(..., max_length=255)
    is_active: bool = True
    role_names: List[str] = Field(default_factory=list, description="Roles to assign on creation (e.g. ['editor', 'viewer'])")


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    roles: List[str] = Field(default_factory=list)
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int


# =============================================================================
# ROLE SCHEMAS
# =============================================================================

class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    permissions: Dict[str, bool] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    roles: List[RoleResponse]
    total: int


class RoleAssignment(BaseModel):
    role_name: str = Field(..., description="Role to assign (admin, operations, finance, editor, viewer)")


class RoleRemoval(BaseModel):
    role_name: str = Field(..., description="Role to remove")


# =============================================================================
# PROJECT ACCESS SCHEMAS
# =============================================================================

class ProjectAccessGrant(BaseModel):
    project_id: UUID
    access_level: str = Field("viewer", description="Access level: viewer, editor, admin")


class ProjectAccessResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: UUID
    access_level: str
    granted_by: Optional[UUID] = None
    granted_at: datetime

    class Config:
        from_attributes = True


class ProjectAccessListResponse(BaseModel):
    grants: List[ProjectAccessResponse]
    total: int


# =============================================================================
# AUDIT LOG SCHEMAS
# =============================================================================

class AuditLogEntry(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    user_email: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    entries: List[AuditLogEntry]
    total: int


# =============================================================================
# AUTH INFO (for /auth/me endpoint)
# =============================================================================

class AuthInfoResponse(BaseModel):
    user_id: UUID
    email: str
    display_name: str
    roles: List[str]
    permissions: Dict[str, bool]
    project_ids: Optional[List[UUID]] = Field(None, description="Accessible project IDs, or null for all-access roles")
