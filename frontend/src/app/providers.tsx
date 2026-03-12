"use client";

import { useEffect } from "react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/layout/app-shell";
import { useAppStore } from "@/stores/app-store";
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

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider>
      <ThemeInit />
      <BadgePoller />
      <AppShell>{children}</AppShell>
    </TooltipProvider>
  );
}
