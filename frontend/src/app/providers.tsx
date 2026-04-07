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
