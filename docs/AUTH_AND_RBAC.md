# DHG AI Factory — Authentication & RBAC

**Added:** April 2026 (Phase 3)
**Pattern:** 4-layer defense-in-depth
**Last Updated:** April 8, 2026

---

## Architecture Overview

Authentication and authorization use a 4-layer defense-in-depth model. Each layer independently validates access, so compromising one layer does not grant access.

```
Internet
  │
  ▼
Layer 1: Cloudflare Access + WAF
  ├── Google OAuth authentication
  ├── DDoS protection, bot filtering
  ├── Sets CF_Authorization cookie (JWT)
  ├── Sets Cf-Access-Jwt-Assertion header
  │
  ▼
Layer 2: Next.js Middleware (Edge Runtime)
  ├── Reads CF_Authorization cookie
  ├── Decodes JWT payload (no signature verification — Edge constraint)
  ├── Route guard: blocks navigation to routes the user's role can't access
  ├── Passes x-user-email header to SSR
  │
  ▼
Layer 3: FastAPI Middleware (registry/auth.py)
  ├── Full JWT signature verification against Cloudflare JWKS
  ├── User resolution from security_users table
  ├── Role + permission aggregation
  ├── Audit log entry for every auth event
  │
  ▼
Layer 4: PostgreSQL RBAC Tables
  ├── 5 security tables enforce data-level access
  ├── Per-project scoping for editor/viewer roles
  └── Immutable audit trail
```

---

## Roles and Permissions

5 roles are seeded into the `security_roles` table. Each has a fixed JSON permission set.

| Role | Description | Key Permissions |
|------|-------------|----------------|
| **admin** | Full system access | All permissions including `users.write`, `users.delete`, `settings.write` |
| **operations** | Project management and team ops | `projects.read/write`, `reviews.read/write`, `audit.read`, `all_projects` |
| **finance** | Financial data access | `projects.read`, `reports.read`, `costs.read`, `all_projects` |
| **editor** | Content editing on assigned projects | `projects.read/write`, `reviews.read/write` (scoped to assigned projects) |
| **viewer** | Read-only on assigned projects | `projects.read`, `reviews.read` (scoped to assigned projects) |

**Project scoping:** Roles with `all_projects: true` (admin, operations, finance) see everything. Roles without it (editor, viewer) only see projects explicitly granted via `security_project_access`.

**Full permission matrix** — defined in `registry/auth.py` `ROLE_DEFINITIONS`.

---

## Database Tables

5 tables added by migration `004_add_security_rbac.py`:

| Table | Purpose |
|-------|---------|
| `security_users` | User identities (email, display_name, cloudflare_id, is_active, last_login) |
| `security_roles` | Role definitions with JSON permission sets |
| `security_user_roles` | Many-to-many user-role assignments (tracks who granted and when) |
| `security_project_access` | Per-project grants for scoped roles (tracks access_level, granted_by) |
| `security_audit_log` | Immutable audit trail (user, action, resource, IP, user agent, timestamp) |

---

## Backend (FastAPI)

### JWT Validation (`registry/auth.py`)

Cloudflare Access JWTs are validated against JWKS public keys:

1. Extract `Cf-Access-Jwt-Assertion` header
2. Fetch JWKS from `https://{team}.cloudflareaccess.com/cdn-cgi/access/certs` (cached 1 hour)
3. Match JWT `kid` to JWKS key (force-refresh if not found — handles key rotation)
4. Verify signature (RS256), audience (`CF_ACCESS_AUD`), and issuer
5. Extract email claim

### FastAPI Dependencies

```python
# Require any authenticated user
@app.get("/endpoint")
async def endpoint(user: AuthenticatedUser = Depends(get_current_user)):
    ...

# Require a specific permission
@app.get("/admin-endpoint")
async def admin_endpoint(user: AuthenticatedUser = Depends(require_permission("users.write"))):
    ...

# Require one of several roles
@app.get("/ops-endpoint")
async def ops_endpoint(user: AuthenticatedUser = Depends(require_role("admin", "operations"))):
    ...
```

### `AuthenticatedUser` Object

Resolved from the database on every authenticated request:

```python
user.id            # UUID
user.email         # str
user.display_name  # str
user.is_active     # bool
user.roles         # List[str] — e.g. ["admin", "operations"]
user.permissions   # dict — aggregated from all roles
user.has_permission("reviews.write")  # bool
user.has_role("admin")                # bool
user.has_any_role("admin", "operations")  # bool
```

### Audit Logging

Every security-relevant action writes to `security_audit_log`:
- `authenticated` — successful login
- `auth_failed` — invalid JWT
- `access_denied_not_registered` — valid JWT but unknown user
- `access_denied_inactive` — disabled account
- `permission_denied` — insufficient permissions
- `role_denied` — wrong role
- CRUD operations on users, roles, project access

Each entry records: user email, action, resource type/ID, IP address, user agent, timestamp.

---

## Security API Endpoints

All at prefix `/api/v1/security`. Authentication required for all endpoints.

### Session
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/auth/me` | Any user | Returns current user info (email, roles, permissions) |
| GET | `/users/me` | Any user | Returns current user profile |

### User Management (admin only)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users` | `users.read` | List all users (paginated) |
| POST | `/users` | `users.write` | Create user |
| GET | `/users/{id}` | `users.read` | Get user by ID |
| PATCH | `/users/{id}` | `users.write` | Update user |
| DELETE | `/users/{id}` | `users.delete` | Deactivate user |

### Role Management (admin only)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/roles` | `roles.read` | List all roles with permissions |
| POST | `/users/{id}/roles` | `roles.write` | Assign role to user |
| DELETE | `/users/{id}/roles/{role}` | `roles.write` | Remove role from user |

### Project Access (admin only)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users/{id}/projects` | `users.read` | List user's project grants |
| POST | `/users/{id}/projects` | `users.write` | Grant project access |
| DELETE | `/users/{id}/projects/{pid}` | `users.write` | Revoke project access |

### Audit Log (admin/operations)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/audit` | `audit.read` | Query audit log (paginated, filterable) |

---

## Frontend Auth

### Session Flow

1. `providers.tsx` calls `useSession()` on app mount
2. `useSession()` hook fetches `/api/auth/me` (unless dev mode)
3. `/api/auth/me` route proxies to registry `/api/v1/security/users/me` with the Cloudflare JWT
4. Response stored in Zustand `session-store.ts` — available app-wide via `useSessionStore()`

### Route Guards

Two layers of route protection:

**Layer 1 — Next.js Middleware** (`middleware.ts`, Edge Runtime):
- Reads `CF_Authorization` cookie
- Decodes JWT payload (base64, no signature verification — Edge can't do JWKS)
- Checks route against `ROUTE_ROLES` map
- Redirects unauthenticated users to `/projects`

**Layer 2 — Client-side** (`lib/permissions.ts`):
- `ROUTE_PERMISSIONS` array defines path/label/section/roles for every route
- `getVisibleRoutes(roles)` filters sidebar navigation
- `canAccessRoute(roles, path)` checks individual routes
- Sidebar only renders routes the user's roles can access

### Dev Mode

Set `NEXT_PUBLIC_SECURITY_DEV_MODE=true` (frontend) and `SECURITY_DEV_MODE=true` (backend):
- Frontend: middleware allows all routes, session store provides admin dev user
- Backend: accepts `X-User-Email` header without JWT, falls back to `dev@digitalharmonyai.com`
- Warnings logged on every dev-mode authentication

---

## Frontend Files

| File | Purpose |
|------|---------|
| `middleware.ts` | Next.js Edge middleware — JWT cookie check, route guard |
| `lib/permissions.ts` | Route-role matrix, visibility helpers |
| `lib/decode-jwt.ts` | Client-side JWT payload decode |
| `stores/session-store.ts` | Zustand auth state (user, roles, permissions) |
| `hooks/use-session.ts` | Session hook (fetch, cache, provide role helpers) |
| `app/api/auth/me/route.ts` | Proxy to registry `/api/v1/security/users/me` |
| `app/api/registry/[...path]/route.ts` | Registry proxy (forwards `Cf-Access-Jwt-Assertion`) |
| `app/providers.tsx` | Session initialization on app mount |
| `components/layout/sidebar.tsx` | Role-aware sidebar navigation |

## Backend Files

| File | Purpose |
|------|---------|
| `registry/auth.py` | JWT validation, user resolution, audit logging, dependency factories |
| `registry/security_endpoints.py` | RBAC admin API (14 endpoints) |
| `registry/security_schemas.py` | Pydantic schemas for security API |
| `registry/models.py` | SQLAlchemy models for 5 security tables |
| `registry/alembic/versions/004_add_security_rbac.py` | Database migration |
| `registry/test_security.py` | 735 lines of security tests |

---

## Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `CF_ACCESS_TEAM_DOMAIN` | Backend | Cloudflare Access team domain (default: `digitalharmonygroup`) |
| `CF_ACCESS_AUD` | Backend | Cloudflare Access application audience tag |
| `SECURITY_DEV_MODE` | Backend | `true` bypasses all auth (dev only) |
| `NEXT_PUBLIC_SECURITY_DEV_MODE` | Frontend | `true` bypasses all auth (dev only) |

---

## Adding a New Role

1. Add the role definition to `ROLE_DEFINITIONS` in `registry/auth.py`
2. Add a migration to insert the role into `security_roles` table
3. Update `ROUTE_ROLES` in `middleware.ts` with routes the role can access
4. Update `ROUTE_PERMISSIONS` in `lib/permissions.ts` with the same routes
5. Run tests: `pytest registry/test_security.py`

## Adding a New Protected Route

1. Add the route to `ROUTE_PERMISSIONS` in `lib/permissions.ts` (this controls sidebar visibility)
2. Add the route to `ROUTE_ROLES` in `middleware.ts` (this controls Edge middleware guard)
3. The two must stay in sync — middleware runs in Edge Runtime and can't import from `lib/`

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| 401 on all requests | `CF_ACCESS_AUD` not set or wrong | Check `.env` matches Cloudflare Access app config |
| 403 "User not registered" | User authenticated via Cloudflare but not in `security_users` table | Create user via admin API or direct DB insert |
| 403 "Missing permission" | User's roles don't include the required permission | Assign appropriate role via admin API |
| Middleware redirects in dev | `NEXT_PUBLIC_SECURITY_DEV_MODE` not set to `true` | Add to `.env.local` in frontend |
| JWKS fetch failure | Network issue reaching Cloudflare | Stale cache is used as fallback; check connectivity |
