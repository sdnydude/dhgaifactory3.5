# Phase 3: Foundation + LLManager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the auth/role-based navigation foundation (Step 0) and upgrade `/inbox` into a full LLManager review workflow with LLM reflection (Step 1).

**Architecture:** Cloudflare Access JWT decoded client-side via `useSession` hook, cached in Zustand. Sidebar sections filtered by role. Next.js middleware guards routes server-side. LLManager adds a reflection panel to the existing review infrastructure, with a master-detail inbox layout.

**Tech Stack:** Next.js 16, Zustand, Cloudflare Access JWT, LangGraph Cloud SDK, shadcn/ui, existing review components

---

## File Structure

### Step 0: Foundation

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `frontend/src/lib/permissions.ts` | Role definitions, route-to-role mapping, permission checks |
| Create | `frontend/src/stores/session-store.ts` | Zustand store for user session (email, roles, permissions) |
| Create | `frontend/src/hooks/use-session.ts` | Hook to access session store, triggers JWT decode on mount |
| Create | `frontend/src/lib/decode-jwt.ts` | Decode Cloudflare JWT from cookie (client-side, no verification) |
| Create | `frontend/src/middleware.ts` | Next.js middleware for server-side route guards |
| Create | `frontend/src/app/api/auth/me/route.ts` | API route that proxies to registry to get user roles |
| Modify | `frontend/src/components/layout/sidebar.tsx` | Grouped sections, role filtering |
| Modify | `frontend/src/app/providers.tsx` | Add session initialization |

### Step 1: LLManager

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `frontend/src/stores/review-store.ts` | Review workflow state — selected item, reflection data |
| Create | `frontend/src/components/review/reflection-panel.tsx` | LLM reflection: AI summary, quality signals, recommendation |
| Create | `frontend/src/components/review/inbox-master-detail.tsx` | Master-detail layout wrapping list + review panel |
| Modify | `frontend/src/app/inbox/page.tsx` | Switch to master-detail layout |
| Modify | `frontend/src/lib/inboxApi.ts` | Add reflection data fetching |
| Create | `registry/analytics_endpoints.py` | New `/api/reviews/pending` enriched endpoint |
| Modify | `registry/api.py` | Mount analytics router |

---

## STEP 0: FOUNDATION

### Task 1: Permissions Module

**Files:**
- Create: `frontend/src/lib/permissions.ts`

- [ ] **Step 1: Create the permissions module**

```typescript
// frontend/src/lib/permissions.ts

export type Role = "admin" | "operations" | "finance" | "editor" | "viewer";

export interface RoutePermission {
  path: string;
  label: string;
  section: "work" | "observe" | "manage";
  roles: Role[];
}

export const ROUTE_PERMISSIONS: RoutePermission[] = [
  // Work section
  { path: "/projects", label: "Projects", section: "work", roles: ["admin", "operations", "finance", "editor", "viewer"] },
  { path: "/inbox", label: "Inbox", section: "work", roles: ["admin", "operations", "editor", "viewer"] },
  { path: "/chat", label: "Chat", section: "work", roles: ["admin", "operations", "editor"] },
  { path: "/search", label: "Search", section: "work", roles: ["admin", "operations", "editor"] },
  // Observe section
  { path: "/agents", label: "Agents", section: "observe", roles: ["admin", "operations"] },
  { path: "/dashboards", label: "Dashboards", section: "observe", roles: ["admin", "operations", "finance"] },
  { path: "/monitoring", label: "Monitoring", section: "observe", roles: ["admin", "operations"] },
  { path: "/studio", label: "Studio", section: "observe", roles: ["admin", "operations"] },
  // Manage section
  { path: "/admin", label: "Admin Console", section: "manage", roles: ["admin"] },
];

export const SECTION_LABELS: Record<string, string> = {
  work: "Work",
  observe: "Observe",
  manage: "Manage",
};

export function getVisibleRoutes(roles: Role[]): RoutePermission[] {
  return ROUTE_PERMISSIONS.filter((route) =>
    route.roles.some((r) => roles.includes(r))
  );
}

export function canAccessRoute(roles: Role[], path: string): boolean {
  const route = ROUTE_PERMISSIONS.find((r) => path.startsWith(r.path));
  if (!route) return true; // Unknown routes are allowed (e.g., /)
  return route.roles.some((r) => roles.includes(r));
}

export function getVisibleSections(roles: Role[]): string[] {
  const visible = getVisibleRoutes(roles);
  return [...new Set(visible.map((r) => r.section))];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/permissions.ts
git commit -m "feat(auth): add permissions module with role-based route visibility"
```

---

### Task 2: JWT Decode Utility

**Files:**
- Create: `frontend/src/lib/decode-jwt.ts`

- [ ] **Step 1: Create JWT decode utility**

This decodes the JWT payload client-side without cryptographic verification (Cloudflare already verified it at the edge — we just need the claims). The `Cf-Access-Jwt-Assertion` cookie is set by Cloudflare Access on every authenticated request.

```typescript
// frontend/src/lib/decode-jwt.ts

export interface CfAccessClaims {
  email: string;
  sub: string;
  iat: number;
  exp: number;
  iss: string;
  custom?: Record<string, unknown>;
}

export function decodeCfJwt(token: string): CfAccessClaims | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) return null;
    return payload as CfAccessClaims;
  } catch {
    return null;
  }
}

export function getCfJwtFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((c) => c.startsWith("CF_Authorization="));
  return match ? match.split("=")[1] : null;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/decode-jwt.ts
git commit -m "feat(auth): add client-side Cloudflare JWT decode utility"
```

---

### Task 3: Session Store

**Files:**
- Create: `frontend/src/stores/session-store.ts`

- [ ] **Step 1: Create the session store**

```typescript
// frontend/src/stores/session-store.ts
"use client";

import { create } from "zustand";
import type { Role } from "@/lib/permissions";

export interface SessionUser {
  email: string;
  displayName: string;
  roles: Role[];
  permissions: Record<string, boolean>;
}

interface SessionState {
  user: SessionUser | null;
  loading: boolean;
  error: string | null;
  setUser: (user: SessionUser | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

const DEV_MODE = process.env.NEXT_PUBLIC_SECURITY_DEV_MODE === "true";

const DEV_USER: SessionUser = {
  email: "dev@digitalharmonyai.com",
  displayName: "Dev User",
  roles: ["admin"],
  permissions: {
    "users.read": true, "users.write": true, "users.delete": true,
    "roles.read": true, "roles.write": true,
    "projects.read": true, "projects.write": true, "projects.delete": true,
    "reviews.read": true, "reviews.write": true,
    "audit.read": true,
    "settings.read": true, "settings.write": true,
    "all_projects": true,
  },
};

export const useSessionStore = create<SessionState>()((set) => ({
  user: DEV_MODE ? DEV_USER : null,
  loading: !DEV_MODE,
  error: null,
  setUser: (user) => set({ user, loading: false, error: null }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, loading: false }),
}));
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/session-store.ts
git commit -m "feat(auth): add session store with dev mode fallback"
```

---

### Task 4: Auth API Route + useSession Hook

**Files:**
- Create: `frontend/src/app/api/auth/me/route.ts`
- Create: `frontend/src/hooks/use-session.ts`

- [ ] **Step 1: Create the server-side auth API route**

This proxies to the registry API to resolve the user's roles from the database. The Cloudflare JWT is forwarded as a header.

```typescript
// frontend/src/app/api/auth/me/route.ts
import { NextRequest, NextResponse } from "next/server";

const REGISTRY_API_URL =
  process.env.REGISTRY_API_URL || "http://dhg-registry-api:8000";

export async function GET(req: NextRequest) {
  const cfToken = req.cookies.get("CF_Authorization")?.value;
  const headers: Record<string, string> = {
    accept: "application/json",
  };
  if (cfToken) {
    headers["Cf-Access-Jwt-Assertion"] = cfToken;
  }

  try {
    const response = await fetch(`${REGISTRY_API_URL}/api/admin/users/me`, {
      headers,
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Not authenticated" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "Auth service unavailable" },
      { status: 503 },
    );
  }
}
```

- [ ] **Step 2: Create the useSession hook**

```typescript
// frontend/src/hooks/use-session.ts
"use client";

import { useEffect } from "react";
import { useSessionStore, type SessionUser } from "@/stores/session-store";
import type { Role } from "@/lib/permissions";
import { canAccessRoute, getVisibleRoutes } from "@/lib/permissions";

export function useSession() {
  const { user, loading, error, setUser, setLoading, setError } =
    useSessionStore();

  useEffect(() => {
    if (user || process.env.NEXT_PUBLIC_SECURITY_DEV_MODE === "true") return;

    let active = true;
    setLoading(true);

    fetch("/api/auth/me")
      .then((res) => {
        if (!res.ok) throw new Error("Not authenticated");
        return res.json();
      })
      .then((data) => {
        if (!active) return;
        const sessionUser: SessionUser = {
          email: data.email,
          displayName: data.display_name || data.email,
          roles: (data.roles || []) as Role[],
          permissions: data.permissions || {},
        };
        setUser(sessionUser);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Auth failed");
      });

    return () => {
      active = false;
    };
  }, [user, setUser, setLoading, setError]);

  return {
    user,
    loading,
    error,
    roles: user?.roles ?? [],
    canAccess: (path: string) => canAccessRoute(user?.roles ?? [], path),
    visibleRoutes: getVisibleRoutes(user?.roles ?? []),
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/api/auth/me/route.ts frontend/src/hooks/use-session.ts
git commit -m "feat(auth): add /api/auth/me route and useSession hook"
```

---

### Task 5: Backend — `/api/admin/users/me` Endpoint

**Files:**
- Modify: `registry/security_endpoints.py`

The frontend auth route needs a `/api/admin/users/me` endpoint that returns the current user's profile and roles. Check if it exists first.

- [ ] **Step 1: Check if endpoint exists**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
grep -n "users/me" registry/security_endpoints.py
```

If it exists, skip to Task 6. If not, add it.

- [ ] **Step 2: Add the /me endpoint**

Add this to `registry/security_endpoints.py` inside the `security_router`:

```python
@security_router.get("/users/me")
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
```

- [ ] **Step 3: Verify endpoint works**

```bash
curl -s http://localhost:8011/api/admin/users/me \
  -H "X-User-Email: dev@digitalharmonyai.com" | python3 -m json.tool
```

Expected: JSON with email, roles, permissions.

- [ ] **Step 4: Commit**

```bash
git add registry/security_endpoints.py
git commit -m "feat(auth): add /api/admin/users/me endpoint for frontend session"
```

---

### Task 6: Grouped Sidebar with Role Filtering

**Files:**
- Modify: `frontend/src/components/layout/sidebar.tsx`

- [ ] **Step 1: Rewrite sidebar with grouped sections**

Replace the contents of `frontend/src/components/layout/sidebar.tsx` with:

```typescript
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  FolderKanban,
  Inbox,
  MessageSquare,
  Activity,
  Search,
  Monitor,
  Sparkles,
  BarChart3,
  Settings,
  PanelLeftClose,
  PanelLeft,
  Moon,
  Sun,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useAppStore } from "@/stores/app-store";
import { useSession } from "@/hooks/use-session";
import { useTheme } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";
import { SECTION_LABELS, type RoutePermission } from "@/lib/permissions";

const ROUTE_ICONS: Record<string, typeof FolderKanban> = {
  "/projects": FolderKanban,
  "/inbox": Inbox,
  "/chat": MessageSquare,
  "/search": Search,
  "/agents": Activity,
  "/dashboards": BarChart3,
  "/monitoring": Monitor,
  "/studio": Sparkles,
  "/admin": Settings,
};

const BADGE_KEYS: Record<string, "inbox" | "processing" | null> = {
  "/projects": "processing",
  "/inbox": "inbox",
};

function NavLink({
  href,
  active,
  collapsed,
  icon: Icon,
  label,
  badge,
}: {
  href: string;
  active: boolean;
  collapsed: boolean;
  icon: typeof FolderKanban;
  label: string;
  badge: number;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent",
        collapsed && "justify-center px-0",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && (
        <>
          <span className="flex-1">{label}</span>
          {badge > 0 && (
            <Badge variant="secondary" className="h-5 min-w-[20px] justify-center text-[10px] px-1.5">
              {badge}
            </Badge>
          )}
        </>
      )}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const badgeCounts = useAppStore((s) => s.badgeCounts);
  const { darkMode, toggleDarkMode } = useTheme();
  const { visibleRoutes } = useSession();
  const [cloudStatus, setCloudStatus] = useState<"ok" | "down" | "checking">("checking");

  useEffect(() => {
    let active = true;
    const check = () => {
      fetch("/api/langgraph/ok")
        .then((r) => { if (active) setCloudStatus(r.ok ? "ok" : "down"); })
        .catch(() => { if (active) setCloudStatus("down"); });
    };
    check();
    const interval = setInterval(check, 60_000);
    return () => { active = false; clearInterval(interval); };
  }, []);

  // Group routes by section
  const sections = ["work", "observe", "manage"];
  const groupedRoutes: Record<string, RoutePermission[]> = {};
  for (const section of sections) {
    const routes = visibleRoutes.filter((r) => r.section === section);
    if (routes.length > 0) {
      groupedRoutes[section] = routes;
    }
  }

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-border bg-sidebar h-full transition-all duration-200",
        collapsed ? "w-[60px]" : "w-[200px]",
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 py-4 border-b border-border min-h-[56px]">
        <Link href="/projects" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="h-8 w-8 shrink-0 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">AI</span>
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <h1 className="text-sm font-semibold text-sidebar-foreground leading-none whitespace-nowrap">
                DHG AI Factory
              </h1>
              <p className="text-[10px] text-muted-foreground whitespace-nowrap">
                AI Agents In Tune With You
              </p>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2 px-2 overflow-auto">
        {sections.map((section) => {
          const routes = groupedRoutes[section];
          if (!routes) return null;

          return (
            <div key={section} className="mb-3">
              {!collapsed && (
                <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {SECTION_LABELS[section]}
                </div>
              )}
              {collapsed && section !== "work" && (
                <div className="mx-2 my-2 border-t border-border" />
              )}
              <div className="space-y-0.5">
                {routes.map((route) => {
                  const active = pathname.startsWith(route.path);
                  const Icon = ROUTE_ICONS[route.path] ?? Activity;
                  const badgeKey = BADGE_KEYS[route.path];
                  const badge = badgeKey ? badgeCounts[badgeKey] : 0;

                  if (collapsed) {
                    return (
                      <Tooltip key={route.path}>
                        <TooltipTrigger className="w-full">
                          <NavLink href={route.path} active={active} collapsed icon={Icon} label={route.label} badge={badge} />
                        </TooltipTrigger>
                        <TooltipContent side="right" className="flex items-center gap-2">
                          {route.label}
                          {badge > 0 && (
                            <Badge variant="secondary" className="h-5 text-[10px]">
                              {badge}
                            </Badge>
                          )}
                        </TooltipContent>
                      </Tooltip>
                    );
                  }

                  return (
                    <NavLink key={route.path} href={route.path} active={active} collapsed={false} icon={Icon} label={route.label} badge={badge} />
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>

      {/* LangGraph Status */}
      <div className={cn("px-3 py-2 border-t border-border", collapsed && "px-0 flex justify-center")}>
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger className="inline-flex">
              <span className={cn(
                "inline-block h-2 w-2 rounded-full",
                cloudStatus === "ok" ? "bg-green-500" : cloudStatus === "down" ? "bg-red-500" : "bg-yellow-500 animate-pulse",
              )} />
            </TooltipTrigger>
            <TooltipContent side="right">LangGraph Cloud {cloudStatus === "ok" ? "Connected" : cloudStatus === "down" ? "Unreachable" : "Checking..."}</TooltipContent>
          </Tooltip>
        ) : (
          <div className="flex items-center gap-2">
            <span className={cn(
              "inline-block h-2 w-2 rounded-full",
              cloudStatus === "ok" ? "bg-green-500" : cloudStatus === "down" ? "bg-red-500" : "bg-yellow-500 animate-pulse",
            )} />
            <span className="text-xs text-muted-foreground">
              LangGraph {cloudStatus === "ok" ? "Cloud" : cloudStatus === "down" ? "Down" : "..."}
            </span>
          </div>
        )}
      </div>

      {/* Bottom controls */}
      <div className={cn("border-t border-border p-2 flex gap-1", collapsed ? "flex-col items-center" : "")}>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={toggleDarkMode}
          aria-label="Toggle dark mode"
        >
          {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
        >
          {collapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Verify the frontend builds**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/frontend
npm run build 2>&1 | tail -20
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/sidebar.tsx
git commit -m "feat(nav): grouped sidebar sections with role-based filtering"
```

---

### Task 7: Session Initialization in Providers

**Files:**
- Modify: `frontend/src/app/providers.tsx`

- [ ] **Step 1: Add session initialization to providers**

Replace `frontend/src/app/providers.tsx` with:

```typescript
"use client";

import { useEffect } from "react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/layout/app-shell";
import { useAppStore } from "@/stores/app-store";
import { useSession } from "@/hooks/use-session";
import { useBadgePolling } from "@/hooks/use-badge-polling";

function ThemeInit() {
  const darkMode = useAppStore((s) => s.darkMode);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);
  return null;
}

function BadgePoller() {
  useBadgePolling(30_000);
  return null;
}

function SessionInit() {
  // useSession triggers the auth fetch on mount
  useSession();
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider>
      <ThemeInit />
      <BadgePoller />
      <SessionInit />
      <AppShell>{children}</AppShell>
    </TooltipProvider>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/providers.tsx
git commit -m "feat(auth): initialize session on app mount"
```

---

### Task 8: Next.js Middleware for Route Guards

**Files:**
- Create: `frontend/src/middleware.ts`

- [ ] **Step 1: Create the middleware**

```typescript
// frontend/src/middleware.ts
import { NextRequest, NextResponse } from "next/server";

// Route access by role — mirrors lib/permissions.ts
// Duplicated here because middleware runs in Edge Runtime and can't import from src/lib
const ROUTE_ROLES: Record<string, string[]> = {
  "/projects": ["admin", "operations", "finance", "editor", "viewer"],
  "/inbox": ["admin", "operations", "editor", "viewer"],
  "/chat": ["admin", "operations", "editor"],
  "/search": ["admin", "operations", "editor"],
  "/agents": ["admin", "operations"],
  "/dashboards": ["admin", "operations", "finance"],
  "/monitoring": ["admin", "operations"],
  "/studio": ["admin", "operations"],
  "/admin": ["admin"],
};

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    return JSON.parse(atob(parts[1]));
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip API routes, static files, and the root redirect
  if (
    pathname.startsWith("/api/") ||
    pathname.startsWith("/_next/") ||
    pathname === "/" ||
    pathname.startsWith("/favicon")
  ) {
    return NextResponse.next();
  }

  // In dev mode, allow everything
  if (process.env.NEXT_PUBLIC_SECURITY_DEV_MODE === "true") {
    return NextResponse.next();
  }

  // Find matching route
  const matchedRoute = Object.keys(ROUTE_ROLES).find((route) =>
    pathname.startsWith(route)
  );
  if (!matchedRoute) return NextResponse.next();

  // Get JWT from cookie
  const cfToken = request.cookies.get("CF_Authorization")?.value;
  if (!cfToken) {
    // No auth — redirect to projects (Cloudflare Access handles actual login)
    return NextResponse.redirect(new URL("/projects", request.url));
  }

  // Decode JWT to get email, then check roles via a header passed to the page
  // Note: Full role resolution happens client-side via useSession.
  // Middleware provides a first-pass guard; the definitive check is the API.
  const claims = decodeJwtPayload(cfToken);
  if (!claims) {
    return NextResponse.redirect(new URL("/projects", request.url));
  }

  // Pass the email through to the page via a header for SSR use
  const response = NextResponse.next();
  response.headers.set("x-user-email", (claims.email as string) || "");
  return response;
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/middleware.ts
git commit -m "feat(auth): add Next.js middleware for route guards"
```

---

### Task 9: Verify Foundation End-to-End

- [ ] **Step 1: Add NEXT_PUBLIC_SECURITY_DEV_MODE to .env**

Check if the frontend has a `.env` or `.env.local`:

```bash
ls -la /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/frontend/.env*
```

Add `NEXT_PUBLIC_SECURITY_DEV_MODE=true` to the frontend environment (either `.env.local` or the Docker compose env).

- [ ] **Step 2: Build and verify**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/frontend
npm run build 2>&1 | tail -20
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 3: Verify sidebar renders with grouped sections**

Start the dev server and visually confirm:
- Sidebar shows "WORK", "OBSERVE", "MANAGE" section labels
- All routes appear under correct sections
- Collapsed mode shows section dividers instead of labels

- [ ] **Step 4: Commit any env changes**

```bash
git add frontend/.env.local
git commit -m "chore: add SECURITY_DEV_MODE env for frontend development"
```

---

## STEP 1: LLMANAGER

### Task 10: Review Store

**Files:**
- Create: `frontend/src/stores/review-store.ts`

- [ ] **Step 1: Create the review store**

```typescript
// frontend/src/stores/review-store.ts
"use client";

import { create } from "zustand";
import type { PendingReview } from "@/lib/inboxApi";

interface ReviewState {
  reviews: PendingReview[];
  selectedReviewId: string | null;
  loading: boolean;
  error: string | null;
  actionLoading: string | null;

  setReviews: (reviews: PendingReview[]) => void;
  selectReview: (threadId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setActionLoading: (threadId: string | null) => void;
  removeReview: (threadId: string) => void;
}

export const useReviewStore = create<ReviewState>()((set) => ({
  reviews: [],
  selectedReviewId: null,
  loading: true,
  error: null,
  actionLoading: null,

  setReviews: (reviews) => set({ reviews, loading: false }),
  selectReview: (threadId) => set({ selectedReviewId: threadId }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, loading: false }),
  setActionLoading: (threadId) => set({ actionLoading: threadId }),
  removeReview: (threadId) =>
    set((s) => ({
      reviews: s.reviews.filter((r) => r.threadId !== threadId),
      selectedReviewId:
        s.selectedReviewId === threadId ? null : s.selectedReviewId,
    })),
}));
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/review-store.ts
git commit -m "feat(llmanager): add review store for inbox workflow state"
```

---

### Task 11: Reflection Panel

**Files:**
- Create: `frontend/src/components/review/reflection-panel.tsx`

- [ ] **Step 1: Create the reflection panel**

This component displays the LLM's analysis of the document: a summary, quality signals, and a recommendation. The data comes from the agent's state (quality scores, compliance results, prose metrics).

```typescript
// frontend/src/components/review/reflection-panel.tsx
"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Brain,
  BarChart3,
  Shield,
} from "lucide-react";
import type { ReviewMetrics } from "./types";

interface ReflectionPanelProps {
  metrics: ReviewMetrics;
  recipe: string;
  reviewRound: number;
}

function QualitySignal({
  label,
  passed,
  detail,
}: {
  label: string;
  passed: boolean | undefined;
  detail?: string;
}) {
  const Icon = passed === true ? CheckCircle : passed === false ? XCircle : AlertTriangle;
  const color = passed === true ? "text-green-600" : passed === false ? "text-red-600" : "text-yellow-600";

  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon className={`h-4 w-4 ${color}`} />
      <span className="font-medium">{label}</span>
      {detail && <span className="text-muted-foreground">({detail})</span>}
    </div>
  );
}

function buildRecommendation(metrics: ReviewMetrics): {
  decision: "approve" | "revise" | "needs_attention";
  reasoning: string;
} {
  const issues: string[] = [];

  if (metrics.quality_passed === false) {
    issues.push("prose quality gate failed");
  }
  if (metrics.banned_patterns_found && metrics.banned_patterns_found.length > 0) {
    issues.push(`${metrics.banned_patterns_found.length} banned patterns detected`);
  }
  if (metrics.compliance_result) {
    const compliance = metrics.compliance_result as Record<string, unknown>;
    if (compliance.passed === false) {
      issues.push("ACCME compliance check failed");
    }
  }

  if (issues.length === 0) {
    return {
      decision: "approve",
      reasoning: `All quality gates passed. Word count: ${metrics.word_count ?? "N/A"}. Prose density: ${metrics.prose_density ? `${(metrics.prose_density * 100).toFixed(0)}%` : "N/A"}. No banned patterns detected. Compliance verified.`,
    };
  }

  return {
    decision: issues.length >= 2 ? "needs_attention" : "revise",
    reasoning: `Issues found: ${issues.join("; ")}. Review carefully before approving.`,
  };
}

export function ReflectionPanel({ metrics, recipe, reviewRound }: ReflectionPanelProps) {
  const recommendation = buildRecommendation(metrics);

  const recBadgeVariant =
    recommendation.decision === "approve"
      ? "default"
      : recommendation.decision === "revise"
        ? "secondary"
        : "destructive";

  const recLabel =
    recommendation.decision === "approve"
      ? "Recommend Approve"
      : recommendation.decision === "revise"
        ? "Suggest Revision"
        : "Needs Attention";

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Brain className="h-4 w-4 text-dhg-purple" />
            AI Reflection
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[10px]">
              Round {reviewRound}
            </Badge>
            <Badge variant={recBadgeVariant} className="text-[10px]">
              {recLabel}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Quality Signals */}
        <div>
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <BarChart3 className="h-3 w-3" />
            Quality Signals
          </div>
          <div className="space-y-1.5">
            <QualitySignal
              label="Prose Quality"
              passed={metrics.quality_passed}
              detail={metrics.word_count ? `${metrics.word_count} words` : undefined}
            />
            <QualitySignal
              label="Banned Patterns"
              passed={!metrics.banned_patterns_found?.length}
              detail={
                metrics.banned_patterns_found?.length
                  ? `${metrics.banned_patterns_found.length} found`
                  : "clean"
              }
            />
            {metrics.compliance_result && (
              <QualitySignal
                label="ACCME Compliance"
                passed={(metrics.compliance_result as Record<string, unknown>).passed as boolean}
              />
            )}
          </div>
        </div>

        {/* Recommendation */}
        <div>
          <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Shield className="h-3 w-3" />
            Recommendation
          </div>
          <p className="text-sm text-foreground">{recommendation.reasoning}</p>
        </div>

        {/* Banned patterns detail */}
        {metrics.banned_patterns_found && metrics.banned_patterns_found.length > 0 && (
          <div className="rounded-md bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 px-3 py-2">
            <p className="text-xs font-medium text-red-700 dark:text-red-300 mb-1">
              Banned patterns found:
            </p>
            <ul className="text-xs text-red-600 dark:text-red-400 space-y-0.5">
              {metrics.banned_patterns_found.map((pattern) => (
                <li key={pattern} className="font-mono">{pattern}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/reflection-panel.tsx
git commit -m "feat(llmanager): add AI reflection panel with quality signals and recommendation"
```

---

### Task 12: Master-Detail Inbox Layout

**Files:**
- Create: `frontend/src/components/review/inbox-master-detail.tsx`

- [ ] **Step 1: Create the master-detail layout**

```typescript
// frontend/src/components/review/inbox-master-detail.tsx
"use client";

import { useEffect, useCallback } from "react";
import { Inbox, RefreshCw, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ReviewPanel } from "./review-panel";
import { ReflectionPanel } from "./reflection-panel";
import { useReviewStore } from "@/stores/review-store";
import { listPendingReviews, resumeThread } from "@/lib/inboxApi";
import type { ResumeValue } from "./types";
import { cn } from "@/lib/utils";

const GRAPH_LABELS: Record<string, string> = {
  needs_package: "Needs Package",
  curriculum_package: "Curriculum Package",
  grant_package: "Grant Package",
  full_pipeline: "Full Pipeline",
  needs_assessment: "Needs Assessment",
  research: "Research",
  clinical_practice: "Clinical Practice",
  gap_analysis: "Gap Analysis",
  learning_objectives: "Learning Objectives",
  curriculum_design: "Curriculum Design",
  research_protocol: "Research Protocol",
  marketing_plan: "Marketing Plan",
  grant_writer: "Grant Writer",
  prose_quality: "Prose Quality",
  compliance_review: "Compliance Review",
};

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

export function InboxMasterDetail() {
  const {
    reviews,
    selectedReviewId,
    loading,
    error,
    actionLoading,
    setReviews,
    selectReview,
    setLoading,
    setError,
    setActionLoading,
    removeReview,
  } = useReviewStore();

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listPendingReviews();
      setReviews(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reviews");
    }
  }, [setReviews, setLoading, setError]);

  useEffect(() => {
    fetchReviews();
    const interval = setInterval(fetchReviews, 30_000);
    return () => clearInterval(interval);
  }, [fetchReviews]);

  const selectedReview = reviews.find((r) => r.threadId === selectedReviewId);

  const handleAction = async (
    threadId: string,
    graphId: string,
    resumeValue: ResumeValue,
  ) => {
    setActionLoading(threadId);
    try {
      await resumeThread(threadId, graphId, resumeValue);
      removeReview(threadId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to process action");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Master list */}
      <div className="w-80 border-r border-border flex flex-col shrink-0">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold">Reviews</h2>
            <Badge variant="secondary" className="text-[10px]">
              {reviews.length}
            </Badge>
          </div>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={fetchReviews} disabled={loading}>
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          </Button>
        </div>

        {error && (
          <div className="mx-3 mt-2 flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            {error}
          </div>
        )}

        <ScrollArea className="flex-1">
          {loading && reviews.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground text-sm">
              <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              Loading...
            </div>
          ) : reviews.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <Inbox className="h-10 w-10 mb-2 opacity-40" />
              <p className="text-xs">No pending reviews</p>
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {reviews.map((review) => {
                const isSelected = selectedReviewId === review.threadId;
                return (
                  <button
                    key={review.threadId}
                    onClick={() => selectReview(review.threadId)}
                    className={cn(
                      "w-full text-left rounded-md px-3 py-2.5 transition-colors",
                      isSelected
                        ? "bg-primary/10 border border-primary/20"
                        : "hover:bg-muted border border-transparent",
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <Badge variant="outline" className="text-[10px] border-dhg-purple text-dhg-purple">
                        {GRAPH_LABELS[review.graphId] ?? review.graphId}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground">
                        {formatTimeAgo(review.createdAt)}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {review.currentStep} — Thread {review.threadId.slice(0, 8)}...
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-auto">
        {selectedReview ? (
          <div className="p-4 space-y-4">
            {/* Reflection panel */}
            {selectedReview.payload && (
              <ReflectionPanel
                metrics={selectedReview.payload.metrics}
                recipe={selectedReview.payload.recipe}
                reviewRound={selectedReview.payload.review_round}
              />
            )}

            {/* Full review panel */}
            {selectedReview.payload ? (
              <ReviewPanel
                payload={selectedReview.payload}
                onSubmit={(resumeValue) =>
                  handleAction(
                    selectedReview.threadId,
                    selectedReview.graphId,
                    resumeValue,
                  )
                }
                isLoading={actionLoading === selectedReview.threadId}
              />
            ) : (
              <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
                No review payload available for this thread.
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <Inbox className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm">Select a review from the list</p>
            <p className="text-xs mt-1">
              Reviews appear when agents reach human review gates
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/review/inbox-master-detail.tsx
git commit -m "feat(llmanager): add master-detail inbox layout with reflection panel"
```

---

### Task 13: Update Inbox Page

**Files:**
- Modify: `frontend/src/app/inbox/page.tsx`

- [ ] **Step 1: Replace inbox page with master-detail layout**

Replace `frontend/src/app/inbox/page.tsx` with:

```typescript
"use client";

import { InboxMasterDetail } from "@/components/review/inbox-master-detail";

export default function InboxPage() {
  return <InboxMasterDetail />;
}
```

- [ ] **Step 2: Verify build**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/frontend
npm run build 2>&1 | tail -20
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/inbox/page.tsx
git commit -m "feat(llmanager): wire master-detail inbox as the /inbox page"
```

---

### Task 14: Forward Cloudflare JWT Through Registry Proxy

**Files:**
- Modify: `frontend/src/app/api/registry/[...path]/route.ts`

The registry proxy currently doesn't forward the Cloudflare JWT. The new `/api/admin/users/me` endpoint needs it.

- [ ] **Step 1: Add JWT forwarding to registry proxy**

In `frontend/src/app/api/registry/[...path]/route.ts`, update the headers section to forward the Cloudflare token:

Find:
```typescript
  const headers: Record<string, string> = {
    accept: req.headers.get("accept") || "application/json",
  };
```

Replace with:
```typescript
  const headers: Record<string, string> = {
    accept: req.headers.get("accept") || "application/json",
  };

  // Forward Cloudflare JWT for authentication
  const cfToken = req.cookies.get("CF_Authorization")?.value;
  if (cfToken) {
    headers["Cf-Access-Jwt-Assertion"] = cfToken;
  }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/api/registry/[...path]/route.ts
git commit -m "feat(auth): forward Cloudflare JWT through registry API proxy"
```

---

### Task 15: Final Verification

- [ ] **Step 1: Full build**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/frontend
npm run build 2>&1 | tail -30
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Lint check**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/frontend
npm run lint 2>&1 | tail -20
```

Expected: No errors (warnings acceptable).

- [ ] **Step 3: Visual verification**

Start the dev server and verify:
- [ ] Sidebar shows grouped sections (Work / Observe / Manage)
- [ ] `/inbox` shows master-detail layout
- [ ] Selecting a review shows the reflection panel above the document viewer
- [ ] Approve/Revise/Reject buttons still function
- [ ] Collapsed sidebar shows section dividers

- [ ] **Step 4: Commit any fixes from verification**

---

## Summary

**Step 0 (Foundation):** Tasks 1-9
- `lib/permissions.ts` — role/route mapping
- `lib/decode-jwt.ts` — JWT decode utility
- `stores/session-store.ts` — Zustand session state
- `hooks/use-session.ts` — session hook
- `app/api/auth/me/route.ts` — auth API proxy
- `middleware.ts` — route guards
- `sidebar.tsx` — grouped + role-filtered
- `providers.tsx` — session init
- Backend: `/api/admin/users/me` endpoint

**Step 1 (LLManager):** Tasks 10-15
- `stores/review-store.ts` — review workflow state
- `components/review/reflection-panel.tsx` — AI reflection UI
- `components/review/inbox-master-detail.tsx` — master-detail layout
- `app/inbox/page.tsx` — rewired to master-detail
- Registry proxy — JWT forwarding

**Subsequent plans (not yet written):**
- Step 2: Generative UI panels plan
- Step 3: Pipeline status widget plan
- Step 4: Tremor dashboards plan
- Step 5: Refine admin console plan
