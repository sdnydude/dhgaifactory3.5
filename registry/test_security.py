"""
Tests for DHG Security / RBAC system.

Covers:
  - Cloudflare JWT validation logic
  - AuthenticatedUser permission model
  - get_current_user dependency (dev mode)
  - Security admin endpoints (user CRUD, role assignment, project access, audit)
  - Permission enforcement (admin vs viewer vs unauthenticated)
  - CORS lockdown verification
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user_id():
    return uuid.uuid4()

@pytest.fixture
def viewer_user_id():
    return uuid.uuid4()

@pytest.fixture
def admin_role_id():
    return uuid.uuid4()

@pytest.fixture
def viewer_role_id():
    return uuid.uuid4()

@pytest.fixture
def editor_role_id():
    return uuid.uuid4()


def _make_mock_user(user_id, email, display_name, is_active=True, roles_data=None):
    """Create a mock SecurityUser with mock user_roles."""
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.display_name = display_name
    user.is_active = is_active
    user.last_login_at = None
    user.created_at = datetime(2026, 4, 6, tzinfo=timezone.utc)
    user.updated_at = datetime(2026, 4, 6, tzinfo=timezone.utc)

    mock_user_roles = []
    if roles_data:
        for role_name, permissions in roles_data:
            mock_role = MagicMock()
            mock_role.name = role_name
            mock_role.permissions = permissions
            mock_ur = MagicMock()
            mock_ur.role = mock_role
            mock_user_roles.append(mock_ur)
    user.user_roles = mock_user_roles
    return user


def _make_authenticated_user(user_id, email, display_name, roles, permissions):
    """Create an AuthenticatedUser directly for dependency override."""
    from auth import AuthenticatedUser
    user_mock = MagicMock()
    user_mock.id = user_id
    user_mock.email = email
    user_mock.display_name = display_name
    user_mock.is_active = True
    return AuthenticatedUser(user=user_mock, roles=roles, permissions=permissions)


@pytest.fixture
def security_client(mock_db, admin_user_id):
    """TestClient with auth overridden to return an admin user."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

    from database import get_db
    from auth import get_current_user, ROLE_DEFINITIONS
    from api import app

    def override_get_db():
        yield mock_db

    admin_permissions = ROLE_DEFINITIONS["admin"]["permissions"]
    admin_auth_user = _make_authenticated_user(
        admin_user_id, "admin@digitalharmonyai.com", "Admin User",
        roles=["admin"], permissions=admin_permissions,
    )

    async def override_get_current_user():
        return admin_auth_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def viewer_client(mock_db, viewer_user_id):
    """TestClient with auth overridden to return a viewer (limited permissions)."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

    from database import get_db
    from auth import get_current_user, ROLE_DEFINITIONS
    from api import app

    def override_get_db():
        yield mock_db

    viewer_permissions = ROLE_DEFINITIONS["viewer"]["permissions"]
    viewer_auth_user = _make_authenticated_user(
        viewer_user_id, "viewer@client.com", "Viewer User",
        roles=["viewer"], permissions=viewer_permissions,
    )

    async def override_get_current_user():
        return viewer_auth_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(mock_db):
    """TestClient with NO auth override — simulates unauthenticated requests."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

    from database import get_db
    from api import app

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    # No get_current_user override — the real dependency will run

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ===========================================================================
# TEST: AuthenticatedUser permission model
# ===========================================================================

class TestAuthenticatedUser:

    def test_has_permission_true(self, admin_user_id):
        user = _make_authenticated_user(
            admin_user_id, "a@b.com", "A",
            roles=["admin"],
            permissions={"users.read": True, "users.write": True},
        )
        assert user.has_permission("users.read") is True
        assert user.has_permission("users.write") is True

    def test_has_permission_false(self, viewer_user_id):
        user = _make_authenticated_user(
            viewer_user_id, "v@b.com", "V",
            roles=["viewer"],
            permissions={"projects.read": True},
        )
        assert user.has_permission("users.write") is False
        assert user.has_permission("nonexistent") is False

    def test_has_role(self, admin_user_id):
        user = _make_authenticated_user(
            admin_user_id, "a@b.com", "A",
            roles=["admin", "operations"],
            permissions={},
        )
        assert user.has_role("admin") is True
        assert user.has_role("operations") is True
        assert user.has_role("viewer") is False

    def test_has_any_role(self, viewer_user_id):
        user = _make_authenticated_user(
            viewer_user_id, "v@b.com", "V",
            roles=["viewer"],
            permissions={},
        )
        assert user.has_any_role("admin", "viewer") is True
        assert user.has_any_role("admin", "operations") is False

    def test_multi_role_permission_aggregation(self):
        """Editor + Finance permissions should merge (union)."""
        from auth import ROLE_DEFINITIONS
        editor_perms = ROLE_DEFINITIONS["editor"]["permissions"]
        finance_perms = ROLE_DEFINITIONS["finance"]["permissions"]
        merged = {**editor_perms, **finance_perms}

        user = _make_authenticated_user(
            uuid.uuid4(), "multi@b.com", "Multi",
            roles=["editor", "finance"],
            permissions=merged,
        )
        assert user.has_permission("projects.write") is True   # from editor
        assert user.has_permission("costs.read") is True       # from finance
        assert user.has_permission("reviews.write") is True    # from editor
        assert user.has_permission("reports.read") is True     # from finance

    def test_role_definitions_completeness(self):
        """All 5 defined roles should exist."""
        from auth import ROLE_DEFINITIONS
        assert set(ROLE_DEFINITIONS.keys()) == {"admin", "operations", "finance", "editor", "viewer"}
        for role_name, definition in ROLE_DEFINITIONS.items():
            assert "description" in definition
            assert "permissions" in definition
            assert isinstance(definition["permissions"], dict)


# ===========================================================================
# TEST: JWT Validation
# ===========================================================================

class TestJWTValidation:

    def test_validate_cf_token_missing_aud_raises(self):
        from auth import validate_cf_token
        with patch("auth.CF_ACCESS_AUD", ""):
            with pytest.raises(ValueError, match="CF_ACCESS_AUD"):
                validate_cf_token("some.jwt.token")

    def test_validate_cf_token_invalid_jwt_raises(self):
        from auth import validate_cf_token
        with patch("auth.CF_ACCESS_AUD", "test-aud"):
            with pytest.raises(Exception):
                validate_cf_token("not.a.valid.jwt")

    def test_jwks_cache_returns_cached(self):
        """After fetching, get_cf_jwks should return cached keys without HTTP call."""
        import auth
        test_keys = {"keys": [{"kid": "test", "kty": "RSA"}]}
        auth._jwks_cache["keys"] = test_keys
        auth._jwks_cache["fetched_at"] = 9999999999.0  # far future

        result = auth.get_cf_jwks()
        assert result == test_keys

        # Clean up
        auth._jwks_cache["keys"] = None
        auth._jwks_cache["fetched_at"] = 0.0

    def test_jwks_cache_force_refresh(self):
        """force_refresh=True should bypass cache (but we mock the HTTP call)."""
        import auth
        auth._jwks_cache["keys"] = {"keys": []}
        auth._jwks_cache["fetched_at"] = 9999999999.0

        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kid": "new"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("auth.httpx.get", return_value=mock_response):
            result = auth.get_cf_jwks(force_refresh=True)
            assert result["keys"][0]["kid"] == "new"

        # Clean up
        auth._jwks_cache["keys"] = None
        auth._jwks_cache["fetched_at"] = 0.0


# ===========================================================================
# TEST: Security Endpoints — Admin operations
# ===========================================================================

class TestSecurityUserEndpoints:

    def test_list_users_as_admin(self, security_client, mock_db):
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.count.return_value = 0
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        response = security_client.get("/api/v1/security/users")
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data

    def test_create_user_as_admin(self, security_client, mock_db, admin_role_id):
        # Mock: no existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock: role lookup returns a role
        mock_role = MagicMock()
        mock_role.id = admin_role_id
        mock_role.name = "viewer"

        # Set up side_effect for multiple .filter().first() calls
        call_count = {"n": 0}

        def filter_side_effect(*args, **kwargs):
            result = MagicMock()
            call_count["n"] += 1
            if call_count["n"] == 1:
                result.first.return_value = None  # no existing user
            else:
                result.first.return_value = mock_role  # role lookup
            return result

        mock_db.query.return_value.filter = MagicMock(side_effect=filter_side_effect)

        # Mock flush to assign a UUID to the new user
        def flush_side_effect():
            pass
        mock_db.flush = MagicMock(side_effect=flush_side_effect)

        # Mock refresh to populate relationships
        def refresh_side_effect(obj):
            if hasattr(obj, 'user_roles'):
                obj.user_roles = []
                obj.id = uuid.uuid4()
                obj.created_at = datetime(2026, 4, 6, tzinfo=timezone.utc)
                obj.updated_at = datetime(2026, 4, 6, tzinfo=timezone.utc)
                obj.last_login_at = None
        mock_db.refresh = MagicMock(side_effect=refresh_side_effect)

        response = security_client.post("/api/v1/security/users", json={
            "email": "newuser@client.com",
            "display_name": "New User",
            "role_names": ["viewer"],
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@client.com"
        assert data["display_name"] == "New User"

    def test_create_user_duplicate_email(self, security_client, mock_db):
        existing = MagicMock()
        existing.email = "dup@test.com"
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        response = security_client.post("/api/v1/security/users", json={
            "email": "dup@test.com",
            "display_name": "Dup User",
        })
        assert response.status_code == 409

    def test_update_user_not_found(self, security_client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = security_client.patch(
            f"/api/v1/security/users/{uuid.uuid4()}",
            json={"display_name": "Updated"},
        )
        assert response.status_code == 404

    def test_delete_user_deactivates(self, security_client, mock_db, admin_user_id):
        target_id = uuid.uuid4()
        target_user = MagicMock()
        target_user.id = target_id
        target_user.email = "target@test.com"
        target_user.is_active = True
        mock_db.query.return_value.filter.return_value.first.return_value = target_user

        response = security_client.delete(f"/api/v1/security/users/{target_id}")
        assert response.status_code == 204
        assert target_user.is_active is False

    def test_delete_self_blocked(self, security_client, mock_db, admin_user_id):
        self_user = MagicMock()
        self_user.id = admin_user_id
        self_user.email = "admin@digitalharmonyai.com"
        mock_db.query.return_value.filter.return_value.first.return_value = self_user

        response = security_client.delete(f"/api/v1/security/users/{admin_user_id}")
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]


# ===========================================================================
# TEST: Role management
# ===========================================================================

class TestRoleEndpoints:

    def test_list_roles(self, security_client, mock_db):
        mock_role = MagicMock()
        mock_role.id = uuid.uuid4()
        mock_role.name = "admin"
        mock_role.description = "Full access"
        mock_role.permissions = {"users.read": True}
        mock_role.created_at = datetime(2026, 4, 6, tzinfo=timezone.utc)

        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_role]

        response = security_client.get("/api/v1/security/roles")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["roles"][0]["name"] == "admin"

    def test_assign_role_user_not_found(self, security_client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = security_client.post(
            f"/api/v1/security/users/{uuid.uuid4()}/roles",
            json={"role_name": "editor"},
        )
        assert response.status_code == 404

    def test_remove_role_not_found(self, security_client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = security_client.delete(
            f"/api/v1/security/users/{uuid.uuid4()}/roles/editor",
        )
        assert response.status_code == 404


# ===========================================================================
# TEST: Project access
# ===========================================================================

class TestProjectAccessEndpoints:

    def test_list_project_access(self, security_client, mock_db):
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        response = security_client.get(f"/api/v1/security/users/{uuid.uuid4()}/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["grants"] == []

    def test_grant_project_access_invalid_level(self, security_client, mock_db):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        response = security_client.post(
            f"/api/v1/security/users/{mock_user.id}/projects",
            json={"project_id": str(uuid.uuid4()), "access_level": "superadmin"},
        )
        assert response.status_code == 400
        assert "access_level" in response.json()["detail"]

    def test_revoke_project_access_not_found(self, security_client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = security_client.delete(
            f"/api/v1/security/users/{uuid.uuid4()}/projects/{uuid.uuid4()}",
        )
        assert response.status_code == 404


# ===========================================================================
# TEST: Audit log
# ===========================================================================

class TestAuditEndpoints:

    def test_list_audit_logs_as_admin(self, security_client, mock_db):
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.count.return_value = 0

        response = security_client.get("/api/v1/security/audit")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data

    def test_list_audit_logs_with_filters(self, security_client, mock_db):
        mock_db.query.return_value.filter.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        response = security_client.get(
            "/api/v1/security/audit",
            params={"action": "login", "user_email": "test@test.com"},
        )
        assert response.status_code == 200


# ===========================================================================
# TEST: Permission enforcement (viewer cannot access admin endpoints)
# ===========================================================================

class TestPermissionEnforcement:

    def test_viewer_cannot_list_users(self, viewer_client):
        response = viewer_client.get("/api/v1/security/users")
        assert response.status_code == 403

    def test_viewer_cannot_create_user(self, viewer_client):
        response = viewer_client.post("/api/v1/security/users", json={
            "email": "hack@evil.com",
            "display_name": "Hacker",
        })
        assert response.status_code == 403

    def test_viewer_cannot_delete_user(self, viewer_client):
        response = viewer_client.delete(f"/api/v1/security/users/{uuid.uuid4()}")
        assert response.status_code == 403

    def test_viewer_cannot_assign_roles(self, viewer_client):
        response = viewer_client.post(
            f"/api/v1/security/users/{uuid.uuid4()}/roles",
            json={"role_name": "admin"},
        )
        assert response.status_code == 403

    def test_viewer_cannot_view_audit(self, viewer_client):
        response = viewer_client.get("/api/v1/security/audit")
        assert response.status_code == 403

    def test_viewer_can_view_auth_me(self, viewer_client, mock_db):
        mock_db.query.return_value.filter.return_value.all.return_value = []

        response = viewer_client.get("/api/v1/security/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["roles"] == ["viewer"]
        assert data["permissions"]["projects.read"] is True

    def test_viewer_can_list_roles(self, viewer_client, mock_db):
        mock_db.query.return_value.order_by.return_value.all.return_value = []

        response = viewer_client.get("/api/v1/security/roles")
        assert response.status_code == 200


# ===========================================================================
# TEST: Unauthenticated access (no auth override — real dependency runs)
# ===========================================================================

class TestUnauthenticatedAccess:

    def test_unauth_cannot_access_auth_me(self, unauth_client):
        response = unauth_client.get("/api/v1/security/auth/me")
        assert response.status_code == 401

    def test_unauth_cannot_list_users(self, unauth_client):
        response = unauth_client.get("/api/v1/security/users")
        assert response.status_code == 401


# ===========================================================================
# TEST: Auth info endpoint
# ===========================================================================

class TestAuthInfoEndpoint:

    def test_auth_me_returns_correct_data(self, security_client, mock_db, admin_user_id):
        mock_db.query.return_value.filter.return_value.all.return_value = []

        response = security_client.get("/api/v1/security/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@digitalharmonyai.com"
        assert data["display_name"] == "Admin User"
        assert "admin" in data["roles"]
        assert data["permissions"]["users.read"] is True
        assert data["permissions"]["all_projects"] is True
        assert data["project_ids"] is None  # admin sees all projects


# ===========================================================================
# TEST: CORS lockdown
# ===========================================================================

class TestCORSLockdown:

    def test_cors_allows_production_origin(self, security_client):
        response = security_client.options(
            "/api/v1/security/auth/me",
            headers={
                "Origin": "https://app.digitalharmonyai.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "https://app.digitalharmonyai.com"

    def test_cors_allows_localhost(self, security_client):
        response = security_client.options(
            "/api/v1/security/auth/me",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_blocks_unknown_origin(self, security_client):
        response = security_client.options(
            "/api/v1/security/auth/me",
            headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware does not set the header for disallowed origins
        assert response.headers.get("access-control-allow-origin") is None


# ===========================================================================
# TEST: Audit log helper
# ===========================================================================

class TestAuditLogHelper:

    def test_write_audit_log_creates_entry(self, mock_db):
        from auth import write_audit_log

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "1.2.3.4", "User-Agent": "TestBot/1.0"}
        mock_request.client.host = "127.0.0.1"

        write_audit_log(
            mock_db,
            "test@test.com",
            "test_action",
            user_id=uuid.uuid4(),
            resource_type="user",
            resource_id="abc-123",
            detail={"key": "value"},
            request=mock_request,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        entry = mock_db.add.call_args[0][0]
        assert entry.user_email == "test@test.com"
        assert entry.action == "test_action"
        assert entry.ip_address == "1.2.3.4"
        assert entry.detail == {"key": "value"}

    def test_write_audit_log_handles_commit_failure(self, mock_db):
        from auth import write_audit_log

        mock_db.commit.side_effect = Exception("DB error")

        # Should not raise — audit log failures are logged, not propagated
        write_audit_log(mock_db, "test@test.com", "failing_action")

        mock_db.rollback.assert_called_once()


# ===========================================================================
# TEST: get_user_project_ids
# ===========================================================================

class TestGetUserProjectIds:

    def test_admin_gets_none(self, mock_db, admin_user_id):
        from auth import get_user_project_ids, ROLE_DEFINITIONS
        admin_perms = ROLE_DEFINITIONS["admin"]["permissions"]
        user = _make_authenticated_user(
            admin_user_id, "a@b.com", "A",
            roles=["admin"], permissions=admin_perms,
        )
        result = get_user_project_ids(mock_db, user)
        assert result is None

    def test_viewer_gets_project_list(self, mock_db, viewer_user_id):
        from auth import get_user_project_ids, ROLE_DEFINITIONS
        viewer_perms = ROLE_DEFINITIONS["viewer"]["permissions"]
        user = _make_authenticated_user(
            viewer_user_id, "v@b.com", "V",
            roles=["viewer"], permissions=viewer_perms,
        )

        project_ids = [uuid.uuid4(), uuid.uuid4()]
        mock_rows = [MagicMock(project_id=pid) for pid in project_ids]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_rows

        result = get_user_project_ids(mock_db, user)
        assert len(result) == 2
        assert set(result) == set(project_ids)

    def test_viewer_with_no_projects_gets_empty_list(self, mock_db, viewer_user_id):
        from auth import get_user_project_ids, ROLE_DEFINITIONS
        viewer_perms = ROLE_DEFINITIONS["viewer"]["permissions"]
        user = _make_authenticated_user(
            viewer_user_id, "v@b.com", "V",
            roles=["viewer"], permissions=viewer_perms,
        )

        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = get_user_project_ids(mock_db, user)
        assert result == []


# ===========================================================================
# TEST: Seed roles function
# ===========================================================================

class TestSeedRoles:

    def test_seed_roles_creates_all_five(self, mock_db):
        from security_endpoints import seed_roles

        mock_db.query.return_value.filter.return_value.first.return_value = None

        seed_roles(mock_db)

        assert mock_db.add.call_count == 5
        mock_db.commit.assert_called_once()

    def test_seed_roles_updates_existing(self, mock_db):
        from security_endpoints import seed_roles

        existing_role = MagicMock()
        existing_role.name = "admin"
        existing_role.description = "old"
        existing_role.permissions = {}

        mock_db.query.return_value.filter.return_value.first.return_value = existing_role

        seed_roles(mock_db)

        assert existing_role.description == "Read-only access to assigned projects"  # last role processed
        mock_db.commit.assert_called_once()
