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
