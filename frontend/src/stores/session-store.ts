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
